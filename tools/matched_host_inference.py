"""Fixed-input numeric diagnostic. No browser, environment, optimizer or learning."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile

import numpy as np

VERSION = "imitation-matched-host-inference-v1"
INPUTS = {
    "matched_inputs.npz": (553101, "455b95f026e78e64b01ea37326f420e76bb45bf39f5eda193118ee24d3cc19ab"),
    "model.zip": (1000930, "25ec7c319b7a9eb11c2e3b184debe12c256730af0a36d11762e75a82f7acdb87"),
    "normalization.pkl": (7385, "59bdee0d177e6724b10e84f9797c5a823e97f1ef81652ed23fb0e3c37b0e2493"),
}
ARRAYS = {
    "raw_observations": (1800, 217), "normalized_observations": (1800, 217),
    "local_predictions": (1800, 2), "remote_predictions_inputs_unverified": (1800, 2),
    "recorded_applied_actions": (1800, 2),
}


class InferenceValidationError(ValueError):
    pass


def require(value, message):
    if not value:
        raise InferenceValidationError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract():
    return {"version": VERSION, "inputs": {
        name: {"size": size, "sha256": digest} for name, (size, digest) in INPUTS.items()},
        "samples": 1800, "observation_dimension": 217, "passes": 2, "batch": 1,
        "threads": 1, "device": "cpu", "maximum_inference_presentations": 3600,
        "maximum_worker_seconds": 120, "control_ticks": 0, "reset_ticks": 0,
        "training_updates": 0}


def check_files(directory):
    directory = Path(directory)
    require(directory.is_absolute() and directory.is_dir() and not directory.is_symlink(),
            "Expected an absolute owned input directory")
    for name, (size, digest) in INPUTS.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink()
                and path.stat().st_size == size and sha(path) == digest,
                "Changed pinned inference input: " + name)


def load_arrays(path):
    # Bound the decoded ZIP before NumPy reads any member. Never allow objects.
    with zipfile.ZipFile(path) as archive:
        require(set(archive.namelist()) == {name + ".npy" for name in ARRAYS}
                and len(archive.infolist()) == len(ARRAYS)
                and all(not item.is_dir() and item.file_size <= 2 * 2**20
                        for item in archive.infolist())
                and sum(item.file_size for item in archive.infolist()) <= 8 * 2**20,
                "Unexpected or oversized decoded inference fixture")
        for key, shape in ARRAYS.items():
            with archive.open(key + ".npy") as stream:
                version = np.lib.format.read_magic(stream)
                require(version in ((1, 0), (2, 0)), "Unsupported inference array header")
                reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                actual_shape, fortran, dtype = reader(stream, max_header_size=4096)
                require(actual_shape == shape and not fortran and dtype == np.dtype("float32"),
                        "Decoded fixture header changed before array allocation")
    with np.load(path, allow_pickle=False) as source:
        arrays = {key: source[key].copy() for key in ARRAYS}
    for key, shape in ARRAYS.items():
        array = arrays[key]
        require(array.dtype == np.float32 and array.shape == shape
                and np.isfinite(array).all(), "Invalid float32 fixture array: " + key)
        if shape[1] == 2:
            require(np.abs(array).max() <= 1, "Illegal archived action")
    return arrays


def compare(actual, expected):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape and actual.size > 0
            and np.isfinite(actual).all() and np.isfinite(expected).all(),
            "Invalid fixed-input comparison")
    error = np.abs(actual.astype(np.float64) - expected.astype(np.float64))
    indices = np.argwhere(error != 0)
    first = None
    if len(indices):
        row, column = (int(i) for i in indices[0])
        first = {"sample": row, "element": column,
                 "actual": float(actual[row, column]), "expected": float(expected[row, column])}
    return {"maximum_absolute_difference": float(error.max()),
            "equal_elements_fraction": float((error == 0).mean()),
            "differing_samples": int(np.any(error != 0, axis=1).sum()), "first_difference": first}


def predict_singletons(model, observations, deadline, on_prediction=None):
    actions = []
    for observation in observations:
        require(time.time() < deadline, "Inference-only worker deadline reached")
        action, _ = model.predict(observation.reshape(1, -1), deterministic=True)
        action = np.asarray(action, dtype=np.float32)
        require(action.shape == (1, 2) and np.isfinite(action).all()
                and np.abs(action).max() <= 1, "Invalid singleton prediction")
        actions.append(action[0])
        if on_prediction is not None:
            on_prediction(len(actions) - 1, action[0])
    return np.stack(actions)


def parameter_sha(model):
    result = hashlib.sha256()
    for name, tensor in sorted(model.policy.state_dict().items()):
        result.update(name.encode())
        result.update(tensor.detach().cpu().numpy().tobytes())
    return result.hexdigest()


def validate_grant(path, inputs, output):
    from deploy.inference_worker import validate_ticket
    import psutil
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 2 * 2**20, "Invalid bounded inference grant file")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    parent = psutil.Process().parent()
    require(sys.platform == "linux" and not os.environ.get("FACTORY_DESKTOP_CDP_PORT")
            and parent is not None and parent.pid == payload["parent_pid"]
            and parent.create_time() == payload["parent_creation_time"],
            "Remote inference requires its exact owned Linux parent")
    require(Path(payload["inputs_dir"]) == inputs and Path(payload["output_dir"]) == output
            and sha(path) == os.environ.get("RL_INFERENCE_GRANT_SHA")
            and sha(Path(payload["claim_file"])) == payload["claim_sha256"],
            "Inference paths/grant/durable claim changed")
    validate_ticket(payload["ticket"], payload["ledger"], time.time(), os.environ)
    from research.provenance import fingerprint
    from research.timing_campaign import PROVENANCE_KEYS
    current = fingerprint()
    require(all(current[key] == payload["provenance"][key] for key in PROVENANCE_KEYS)
            and sha(Path(__file__).resolve()) == payload["tool_sha256"],
            "Inference source/tool changed after parent admission")
    require(Path(payload["claim_file"]).is_absolute()
            and Path(payload["claim_file"]).parent == output.parent,
            "Claim is outside the owned inference output parent")
    require(time.time() < payload["worker_deadline_epoch"]
            <= min(payload["ticket"]["deadline_epoch"] - 60, time.time() + 120),
            "Changed child worker deadline")
    return payload


def run(inputs, output, *, deadline, remote=False):
    import pickle
    import torch
    import stable_baselines3
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import VecNormalize
    from research.imitation_train import require_model_settings, settings
    from research.provenance import fingerprint
    require(time.time() < deadline <= time.time() + 120, "Invalid inference-only wall cap")
    inputs, output = Path(inputs), Path(output)
    check_files(inputs)
    arrays = load_arrays(inputs / "matched_inputs.npz")
    if remote:
        require(platform.python_version() == "3.11.17" and torch.__version__ == "2.6.0+cpu"
                and np.__version__ == "2.4.3" and stable_baselines3.__version__ == "2.7.1",
                "Fresh Linux dependencies differ from the declared recorded study")
    torch.set_num_threads(1)
    model = PPO.load(str(inputs / "model.zip"), device="cpu")
    require_model_settings(model, settings("behavior_cloning_only", False))
    require(model.seed == 7 and model.num_timesteps == 0, "Selected clone/settings changed")
    # Deserialization is restricted to our owned, exact hash-verified artifact.
    with (inputs / "normalization.pkl").open("rb") as handle:
        normalizer = pickle.load(handle)
    require(isinstance(normalizer, VecNormalize) and not normalizer.training
            and normalizer.norm_obs and not normalizer.norm_reward
            and normalizer.gamma == model.gamma and normalizer.obs_rms.mean.shape == (217,),
            "Invalid frozen normalizer")
    parameters = parameter_sha(model)
    rms = {key: np.asarray(getattr(normalizer.obs_rms, key)).copy() for key in ("mean", "var", "count")}
    require(output.is_absolute() and not output.exists(), "Use a fresh inference-only output directory")
    output.mkdir()
    report = {"contract": contract(), "kind": "remote_matched_host" if remote else "local_pipeline_validation",
              "status": "running", "provenance": fingerprint(), "tool_sha256": sha(Path(__file__).resolve()),
              "dependencies": {"python": platform.python_version(), "torch": torch.__version__,
                               "numpy": np.__version__, "sb3": stable_baselines3.__version__,
                               "platform": platform.platform(), "cpu_capability": torch.backends.cpu.get_cpu_capability(),
                               "device": "cpu", "threads": torch.get_num_threads()},
              "normalized_input_sha256": hashlib.sha256(
                  arrays["normalized_observations"].astype("<f4").tobytes()).hexdigest(),
              "actual_inference_presentations": 0, "controlled_ticks": 0, "reset_ticks": 0,
              "training_updates": 0, "parameters_sha256": parameters,
              "raw_normalization_comparison": compare(
                  normalizer.normalize_obs(arrays["raw_observations"]), arrays["normalized_observations"]),
              "limit": "Matched archived inputs only. Not historical equal-state proof, controller robustness, "
                       "Torch-build-only causality, held-out success or summit promotion."}

    def save():
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")

    save()
    partial = (output / "inference_presentations.jsonl").open("x", encoding="utf-8")
    def progress(sample, action):
        report["actual_inference_presentations"] += 1
        require(report["actual_inference_presentations"] <= 3600, "Inference presentation budget exceeded")
        partial.write(json.dumps({"presentation": report["actual_inference_presentations"],
                                  "sample": sample, "action": action.tolist()}) + "\n")
        partial.flush()
        if report["actual_inference_presentations"] % 100 == 0:
            save()
    try:
        first = predict_singletons(model, arrays["normalized_observations"], deadline, progress)
        report["versus_local_archived_same_inputs"] = compare(first, arrays["local_predictions"])
        report["versus_historical_remote_actions_inputs_unverified"] = compare(
            first, arrays["remote_predictions_inputs_unverified"])
        save()
        second = predict_singletons(model, arrays["normalized_observations"], deadline, progress)
    finally:
        partial.close()
        save()
    report["singleton_repeat_comparison"] = compare(second, first)
    require(parameter_sha(model) == parameters and model.num_timesteps == 0
            and all(np.array_equal(value, np.asarray(getattr(normalizer.obs_rms, key)))
                    for key, value in rms.items()), "Inference mutated model/normalizer")
    check_files(inputs)
    require(time.time() < deadline, "Inference-only worker exceeded its wall cap")
    report["parameters_timestep_rms_and_input_files_unchanged"] = True
    report["status"] = "inference_complete_no_goal_promotion"
    np.savez_compressed(output / "predictions.npz", first=first, second=second)
    save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--grant", type=Path)
    parser.add_argument("--local-diagnostic", action="store_true")
    args = parser.parse_args()
    require(args.inputs_dir.is_absolute() and args.output_dir.is_absolute(), "Use absolute owned paths")
    require(bool(args.grant) != args.local_diagnostic, "Choose admitted remote or bounded local diagnostic")
    grant = validate_grant(args.grant, args.inputs_dir, args.output_dir) if args.grant else None
    deadline = grant["worker_deadline_epoch"] if grant else time.time() + 120
    result = run(args.inputs_dir, args.output_dir, deadline=deadline, remote=grant is not None)
    print(json.dumps({key: result[key] for key in (
        "kind", "status", "actual_inference_presentations", "controlled_ticks", "training_updates")}), flush=True)


if __name__ == "__main__":
    main()
