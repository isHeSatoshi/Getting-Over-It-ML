"""Bounded real-game evaluator checks with an untrained constant-action fixture."""
import argparse
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.browser_bridge import BrowserBridge, ROOT
from research.env import RealGettingOverItEnv
from research.evaluation_cases import STANDARD_CASES
from research.fast_bridge import FastBridge
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.train import evaluate


class ConstantFixture:
    def __init__(self, gamma):
        self.gamma = gamma
        self.observations = []

    def predict(self, observation, deterministic=True):
        self.observations.append(observation.copy())
        return np.asarray([[0.0, -0.625]], dtype=np.float32), None


def check(reference, fast, ticks):
    reward = RewardConfig()
    shape = RealGettingOverItEnv(bridge=reference).observation_space.shape
    report = {"purpose": "NOT_POLICY_SUCCESS: untrained evaluator/physics fixture",
              "controlled_ticks_per_case": ticks, "cases": {}}
    evidence = {}
    for repeat in (1, 4):
        normalization = SimpleNamespace(gamma=reward.gamma(repeat), norm_reward=False,
                                        obs_rms=RunningMeanStd(shape=shape))
        records, observations = {}, {}
        for name, bridge in (("reference", reference), ("fast", fast)):
            model = ConstantFixture(normalization.gamma)
            records[name] = evaluate(
                model, normalization, bridge, "absolute", True, ticks // repeat, (),
                cases=STANDARD_CASES, frame_skip=repeat, physical_case_clock=True)
            observations[name] = np.concatenate(model.observations)
        if records["reference"] != records["fast"]:
            raise AssertionError("Reference/fast evaluation traces differ")
        np.testing.assert_allclose(observations["reference"], observations["fast"],
                                   rtol=0, atol=1e-6)
        observation_error = float(np.max(np.abs(observations["reference"] - observations["fast"])))
        if repeat == 4:
            for name, bridge in (("reference", reference), ("fast", fast)):
                model = ConstantFixture(normalization.gamma)
                legacy = evaluate(model, normalization, bridge, "absolute", True, ticks // repeat,
                                  (), cases=STANDARD_CASES)
                timed_legacy = [{k: v for k, v in record.items() if k not in (
                    "timing_contract", "controlled_physics_ticks", "reset_settling_physics_ticks")}
                    for record in records[name]]
                if legacy != timed_legacy:
                    raise AssertionError("Explicit four-tick clock changed legacy traces")
                np.testing.assert_array_equal(np.concatenate(model.observations), observations[name])
                records[name + "_legacy"] = legacy
        for record in records["reference"]:
            if record["controlled_physics_ticks"] != ticks:
                raise AssertionError("Fixture did not consume its controlled tick budget")
            if record["reset_settling_physics_ticks"] != 240:
                raise AssertionError("Initial and automatic reset settling work was not counted")
            report["cases"][f"repeat_{repeat}_{record['case']['name']}"] = {
                "reference_fast_trace_equal": True, "max_normalized_observation_error": observation_error,
                "legacy_trace_equal": True if repeat == 4 else None,
                "controlled_ticks": record["controlled_physics_ticks"],
                "reset_settling_ticks": record["reset_settling_physics_ticks"],
                "retained_gain": record["final"]["retained_gain"],
                "success": record["final"]["success"],
            }
        evidence[f"repeat_{repeat}"] = records
    return report, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticks", type=int, default=96, help="Controlled ticks per case, max 128")
    args = parser.parse_args()
    if not 16 <= args.ticks <= 128 or args.ticks % 4:
        parser.error("Fixture budget must be 16..128 controlled ticks, divisible by four")
    output = ROOT / "artifacts" / (
        "evaluation_timing_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    with BrowserBridge(driver="selenium", headless=False) as reference, FastBridge(headless=False) as fast:
        report, evidence = check(reference, fast, args.ticks)
    report["provenance"] = fingerprint()
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "traces.json").write_text(json.dumps(evidence), encoding="utf-8")
    print(json.dumps(report["cases"], indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
