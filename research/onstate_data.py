"""Admit captured successful learner-state controls without an off-state oracle."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.demonstrations import (
    conflict_summary, game_contract_matches, load as load_demonstrations, require)
from research.onstate_study import ARMS, plan
from research.provenance import fingerprint
from research.study_metrics import benchmark_contract
from tools.imitation_noise_probe import MaskedNoise
from tools.matched_host_inference import load_arrays

VERSION = "admitted-logged-success-data-v1"
MAX_BYTES = 8 * 2**20
SOURCE_FILES = {
    "original_data": "f97fdda3397e432d1dbf586fe1055cdfb94ef81172d1962378a8559892b88537",
    "captured_replay": "455b95f026e78e64b01ea37326f420e76bb45bf39f5eda193118ee24d3cc19ab",
    "successful_feedback": "20ea8c65c3d53fbaaa93c8c8807015a731363aa2fbac55fa72867288f40aa3b1",
}
ARRAY_SPEC = {
    "observations": ((5376, 217), np.dtype("float32")),
    "normalized_observations": ((5376, 217), np.dtype("float32")),
    "actions": ((5376, 2), np.dtype("float32")),
    "source_ids": ((5376,), np.dtype("int64")),
    "source_rows": ((5376,), np.dtype("int64")),
}
EXPECTED_ARRAY_HASHES = {
    "original_observations": "49bd40889fd6d462337a724adee84a8de2abed57ef2bf07a7660b59d99605304",
    "original_actions": "0519e6df1ca84057e47dc38dcf696823bb03bd02fd00fdc96ac5cf102fe83421",
    "learner_observations": "20b69de93f36eb73fef1eb94dc3b73a53c44f29218b4c83c85bf62f8a952b408",
    "learner_normalized_observations": "d398647de2f561181993b387f7b80df66a31c37fad67feffdc4f20c6a82d329a",
    "learner_actions": "2cc7ff26a43a44aa202e5fa5d035ab553b638228920df8af86c3821de83996ee",
    "original_source_rows": "3b4c6a54e62cf733ba4f6bd1f9150d356a659ae04ef34b0185ce1441676facb7",
}
_DATA_TOKEN = object()


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def trusted_file(path, maximum, expected=None):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= maximum, "Untrusted or oversized data source")
    payload = path.read_bytes()
    require(len(payload) <= maximum and (expected is None
            or hashlib.sha256(payload).hexdigest() == expected), "Changed pinned data source")
    return payload


def normalizer(observations):
    rms = RunningMeanStd(shape=(217,))
    rms.update(observations)
    return rms


def normalize(observations, rms):
    return np.clip((observations - rms.mean) / np.sqrt(rms.var + 1e-8), -10, 10).astype(np.float32)


def validate_arrays(arrays):
    require(set(arrays) == set(ARRAY_SPEC), "Unexpected admitted data arrays")
    for key, (shape, dtype) in ARRAY_SPEC.items():
        value = arrays[key]
        require(value.shape == shape and value.dtype == dtype and np.isfinite(value).all(),
                "Invalid admitted data shape/dtype/values: " + key)
    require(np.abs(arrays["actions"]).max() <= 1
            and np.array_equal(arrays["source_ids"], np.r_[np.zeros(3576, dtype=np.int64),
                                                         np.ones(1800, dtype=np.int64)]),
            "Illegal controls or changed source ranges")
    require(np.array_equal(arrays["source_rows"][3576:], np.arange(1800))
            and digest(arrays["source_rows"][:3576]) == EXPECTED_ARRAY_HASHES["original_source_rows"],
            "Changed pre-action source row alignment")
    parts = {
        "original_observations": arrays["observations"][:3576],
        "original_actions": arrays["actions"][:3576],
        "learner_observations": arrays["observations"][3576:],
        "learner_normalized_observations": arrays["normalized_observations"][3576:],
        "learner_actions": arrays["actions"][3576:],
    }
    for name, value in parts.items():
        require(digest(value) == EXPECTED_ARRAY_HASHES[name], "Changed admitted logged array: " + name)
    rms = normalizer(arrays["observations"][:3576])
    require(np.array_equal(normalize(arrays["observations"], rms), arrays["normalized_observations"]),
            "Data does not normalize exactly under original frozen RMS")
    return rms


def validate_feedback(feedback, replay):
    rows = feedback["rows"]
    require(feedback["condition"] == "full_noise_8105" and len(rows) == 1800
            and feedback["control_ticks"] == 1800 and feedback["reset_ticks"] == 240,
            "Changed selected legal feedback episode")
    inputs = np.asarray([row["pre_observation"] for row in rows], dtype=np.float32)
    actions = np.asarray([row["applied_action"] for row in rows], dtype=np.float32)
    require(np.array_equal(inputs, replay["normalized_observations"])
            and np.array_equal(actions, replay["recorded_applied_actions"]),
            "Captured raw replay is not the exact logged pre-action/control pairing")
    schedule = MaskedNoise("full_noise_8105")
    for tick, row in enumerate(rows):
        require(np.array_equal(schedule.apply([row["action"]], tick)[0], actions[tick])
                and row["pre_state"]["tick"] == 120 + tick
                and row["post_state"]["tick"] == 121 + tick,
                "Changed legal noise clock or pre-action physical alignment")
        if tick:
            require(row["pre_observation"] == rows[tick-1]["observation"],
                    "Discontinuous normalized observation history")
        require(not row["info"]["success"] and not row["info"]["dead"],
                "Selected data episode terminated before the declared horizon")
    final = feedback["final"]
    require(final == rows[-1]["info"] and final["milestone_contract"] == benchmark_contract(True)
            and final["milestone_success"]["first_ledge_v1"] is True
            and final["milestone_success"]["first_platform_support_diagnostic_v2"] is True,
            "Selected logged episode lacks the reviewed frozen hold")


def derive(output, original_directory, replay_file, feedback_file, current=None):
    output, original_directory = Path(output), Path(original_directory)
    require(output.is_absolute() and not output.exists(), "Use a new absolute derived-data directory")
    current = fingerprint() if current is None else current
    original, metadata = load_demonstrations(original_directory, current)
    require(metadata["data_sha256"] == SOURCE_FILES["original_data"]
            and int(original["eligible"].sum()) == 3576, "Changed eligible original corpus")
    trusted_file(replay_file, 2 * 2**20, SOURCE_FILES["captured_replay"])
    replay = load_arrays(Path(replay_file))
    # Recheck after decode, so a changed archive cannot enter an admitted corpus.
    trusted_file(replay_file, 2 * 2**20, SOURCE_FILES["captured_replay"])
    feedback = json.loads(trusted_file(feedback_file, 64 * 2**20, SOURCE_FILES["successful_feedback"]))
    validate_feedback(feedback, replay)
    selected = original["eligible"]
    observations = np.concatenate((original["observations"][selected], replay["raw_observations"]))
    rms = normalizer(original["observations"][selected])
    arrays = {
        "observations": observations,
        "normalized_observations": np.concatenate((normalize(original["observations"][selected], rms),
                                                  replay["normalized_observations"])),
        "actions": np.concatenate((original["actions"][selected], replay["recorded_applied_actions"])),
        "source_ids": np.r_[np.zeros(3576, dtype=np.int64), np.ones(1800, dtype=np.int64)],
        "source_rows": np.r_[np.flatnonzero(selected), np.arange(1800)].astype(np.int64),
    }
    validate_arrays(arrays)
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "data.npz", **arrays)
    record = {
        "version": VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": current, "source_files": SOURCE_FILES,
        "array_hashes": EXPECTED_ARRAY_HASHES,
        "data_sha256": hashlib.sha256((output / "data.npz").read_bytes()).hexdigest(),
        "rows": {"original": 3576, "logged_success": 1800, "total": 5376},
        "normalization": {"original_samples": 3576, "frozen": True, "clip_obs": 10.0, "epsilon": 1e-8},
        "sampling_and_selection": plan()["data"],
        "exact_input_conflicts": conflict_summary(arrays["normalized_observations"], arrays["actions"]),
        "ordinary_start": True, "privileged_resets": False, "inverse_normalization": False,
        "derivation_game_ticks": 0, "training_updates": 0,
        "limit": "Selected logged controls, not a corrective expert or independent learned robustness",
    }
    (output / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def load_archive(path):
    trusted_file(path, MAX_BYTES)
    with zipfile.ZipFile(path) as archive:
        require(len(archive.infolist()) == len(ARRAY_SPEC)
                and set(archive.namelist()) == {key + ".npy" for key in ARRAY_SPEC}
                and sum(item.file_size for item in archive.infolist()) <= 12 * 2**20,
                "Unexpected or oversized decoded admitted data")
        for key, (shape, dtype) in ARRAY_SPEC.items():
            with archive.open(key + ".npy") as stream:
                version = np.lib.format.read_magic(stream)
                require(version in ((1, 0), (2, 0)), "Unsupported data array header")
                reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                actual, fortran, actual_dtype = reader(stream, max_header_size=4096)
                require(actual == shape and not fortran and actual_dtype == dtype,
                        "Wrong admitted array header before allocation")
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in ARRAY_SPEC}


class OnStateData:
    """Hash-validated captured data and source-balanced sampler, not a run permit."""
    def __init__(self, arrays, record, token=None):
        require(token is _DATA_TOKEN, "Use the validated admitted data loader")
        self.rms = validate_arrays(arrays)
        self.arrays, self.record = arrays, record
        for value in arrays.values():
            value.flags.writeable = False

    def training_arrays(self, arm):
        require(arm in ARMS, "Unknown data-comparison arm")
        end = 3576 if arm == ARMS[0] else 5376
        return self.arrays["observations"][:end], self.arrays["actions"][:end]

    def validate_cloning(self, normalization, observations, actions, arm):
        rms = validate_arrays(self.arrays)
        expected = self.training_arrays(arm)
        require(np.array_equal(observations, expected[0]) and np.array_equal(actions, expected[1]),
                "Cloning labels differ from admitted logged data")
        require(normalization.training is False and normalization.clip_obs == 10
                and normalization.epsilon == 1e-8
                and all(np.array_equal(np.asarray(getattr(normalization.obs_rms, key)),
                                       np.asarray(getattr(rms, key))) for key in ("mean", "var", "count")),
                "On-state cloning must retain the exact original frozen RMS")

    def sample_indices(self, arm, rng, batch_size):
        require(arm in ARMS and type(batch_size) is int and batch_size > 0
                and batch_size % 4 == 0, "Source-balanced batch must be divisible by four")
        new = 0 if arm == ARMS[0] else batch_size // 4
        indices = np.r_[rng.integers(0, 3576, batch_size-new),
                        rng.integers(3576, 5376, new)]
        return rng.permutation(indices)


def load(directory, current=None):
    directory = Path(directory)
    require(directory.is_absolute() and directory.is_dir() and not directory.is_symlink(),
            "Use an absolute admitted data directory")
    record = json.loads(trusted_file(directory / "manifest.json", 2 * 2**20))
    require(record["version"] == VERSION and record["source_files"] == SOURCE_FILES
            and record["array_hashes"] == EXPECTED_ARRAY_HASHES
            and record["rows"] == {"original": 3576, "logged_success": 1800, "total": 5376}
            and record["sampling_and_selection"] == json.loads(json.dumps(plan()["data"]))
            and record["ordinary_start"] is True and record["privileged_resets"] is False
            and record["inverse_normalization"] is False
            and record["derivation_game_ticks"] == record["training_updates"] == 0
            and record["normalization"] == {"original_samples": 3576, "frozen": True,
                                           "clip_obs": 10.0, "epsilon": 1e-8},
            "Changed admitted data declaration or selection")
    game_contract_matches(record["provenance"], fingerprint() if current is None else current)
    path = directory / "data.npz"
    trusted_file(path, MAX_BYTES, record["data_sha256"])
    arrays = load_archive(path)
    trusted_file(path, MAX_BYTES, record["data_sha256"])
    require(record["exact_input_conflicts"] == conflict_summary(
        arrays["normalized_observations"], arrays["actions"]), "Hidden target ambiguity change")
    return OnStateData(arrays, record, _DATA_TOKEN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--replay", required=True, type=Path)
    parser.add_argument("--feedback", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    derive(args.output_dir, args.original, args.replay, args.feedback)
    print("Prepared logged-state data, no training:", args.output_dir)


if __name__ == "__main__":
    main()
