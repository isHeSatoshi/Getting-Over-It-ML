"""Bounded fixed-input inference comparisons. No physics, training, or promotion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from research.browser_bridge import ROOT
from research.provenance import fingerprint


def inputs_from_records(records, dimension):
    observations, expected = [], []
    if not 2 <= len(records) <= 513:
        raise ValueError("Inference trace must contain 2..513 records")
    for current, following in zip(records, records[1:]):
        # The trace records next observations; after VecEnv auto-reset they
        # belong to a new episode and must not be paired as if continuous.
        if current.get("state") is None:
            continue
        observation = np.asarray(current["observation"], dtype=np.float32)
        action = np.asarray(following["action"], dtype=np.float32)
        if (observation.shape != (dimension,) or action.shape != (2,)
                or not np.isfinite(observation).all() or not np.isfinite(action).all()):
            raise ValueError("Invalid fixed inference input/action")
        observations.append(observation)
        expected.append(action)
    if not observations:
        raise ValueError("No continuous fixed inference pairs")
    return np.stack(observations), np.stack(expected)


def predict_batches(model, observations, batch_size):
    if not isinstance(batch_size, int) or batch_size < 1 or not len(observations):
        raise ValueError("Invalid inference batch size")
    actions = []
    for offset in range(0, len(observations), batch_size):
        predicted, _ = model.predict(observations[offset:offset + batch_size], deterministic=True)
        predicted = np.asarray(predicted, dtype=np.float32)
        if predicted.shape != (len(observations[offset:offset + batch_size]), 2):
            raise ValueError("Unexpected policy output shape")
        if not np.isfinite(predicted).all():
            raise ValueError("Non-finite policy inference")
        actions.append(predicted)
    return np.concatenate(actions)


def difference(a, b):
    delta = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return {"max_normalized_action_difference": float(delta.max()),
            "max_pointer_difference_pixels": float(delta.max() * 128),
            "exactly_equal_elements_fraction": float((delta == 0).mean())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", required=True, type=Path, help="Trusted saved policy directory")
    parser.add_argument("--trace", required=True, type=Path, help="Local closed-loop policy trace")
    args = parser.parse_args()
    if not args.trial.is_absolute() or not args.trace.is_absolute():
        parser.error("Pass absolute trusted artifact paths")
    if args.trace.stat().st_size > 10 * 1024 * 1024:
        parser.error("Inference fixture trace is capped at 10 MiB")
    manifest = json.loads((args.trial / "manifest.json").read_text(encoding="utf-8"))
    current = fingerprint()
    for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
        if manifest[key] != current[key]:
            raise ValueError("Saved policy game fingerprint mismatch")
    import torch
    from stable_baselines3 import PPO, SAC
    algorithm = PPO if manifest["config"]["algorithm"] == "ppo" else SAC
    model = algorithm.load(str(args.trial / "model.zip"), device="cpu")
    trace_bytes = args.trace.read_bytes()
    trace = json.loads(trace_bytes)
    records = trace.get("policy_reference", trace.get("reference"))
    if not isinstance(records, list):
        raise ValueError("Expected a recorded policy reference trace")
    observations, expected = inputs_from_records(records, model.observation_space.shape[0])
    output = ROOT / "artifacts" / (
        "inference_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "provenance": current, "trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "model_sha256": hashlib.sha256((args.trial / "model.zip").read_bytes()).hexdigest(),
        "torch": torch.__version__, "numpy": np.__version__, "device": "cpu",
        "samples": len(observations), "input_shape": list(observations.shape),
        "input_float32_sha256": hashlib.sha256(observations.astype("<f4").tobytes()).hexdigest(),
        "input_units": "Already normalized float32 observations; no normalizer mutation",
        "limit": "Within-host fixed-input numeric differences, not cross-host causality "
                 "or a robust control/completion result",
        "variants": {},
    }
    original_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(1)
        baseline = predict_batches(model, observations, 1)
        report["recorded_singleton_reproduction"] = difference(baseline, expected)
        report["variants"]["singleton_repeat"] = difference(
            baseline, predict_batches(model, observations, 1))
        for batch in (8, len(observations)):
            report["variants"][f"batch_{batch}"] = difference(
                baseline, predict_batches(model, observations, batch))
        for threads in (2, 4):
            torch.set_num_threads(threads)
            report["variants"][f"singleton_threads_{threads}"] = difference(
                baseline, predict_batches(model, observations, 1))
    finally:
        torch.set_num_threads(original_threads)
    (output / "fixture.json").write_text(json.dumps({
        "normalized_observations": observations.tolist(), "expected_singleton_actions": expected.tolist(),
    }), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "provenance"}, indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
