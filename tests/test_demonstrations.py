import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.demonstrations import (
    VERSION, TRAINING_CASES, collect, conflict_summary, load, save, validate_arrays)
from research.evaluation_cases import EvaluationCase, STANDARD_CASES
from research.reward import RewardConfig


def provenance():
    from research.demonstrations import CRITICAL
    return {"project_sha256": "project", "runtime_sha256": "game",
            "asset_set_sha256": "assets", "source_sha256": {k: "sha" for k in CRITICAL}}


def metadata(samples=4, passed=True):
    return {"version": VERSION, "ordinary_start": True, "placement": False, "training": False,
            "frame_skip": 1, "action_mode": "absolute", "reward_contract": RewardConfig().describe(1),
            "provenance": provenance(), "episodes": [{
                "controlled_ticks": samples,
                "warmup_ticks": 0,
                "final": {"milestone_success": {"first_ledge_v1": passed}},
            }]}


def arrays():
    return {"observations": np.zeros((4, 217), dtype=np.float32),
            "actions": np.zeros((4, 2), dtype=np.float32),
            "episode_ids": np.zeros(4, dtype=np.int64),
            "eligible": np.ones(4, dtype=np.bool_)}


class Fixture:
    frame_skip = 1
    action_mode = "absolute"

    def reset(self, seed=None):
        self.state = {"tick": 120}
        self.index = 0
        return np.full(217, 0, dtype=np.float32), {}

    def step(self, action):
        self.index += 1
        self.state["tick"] += 1
        return (np.full(217, self.index, dtype=np.float32), 0, False, self.index == 4,
                {"physics_ticks": 1, "milestone_success": {"first_ledge_v1": False}})


class DemonstrationTests(unittest.TestCase):
    def test_pre_action_observation_and_terminal_boundary_are_correct(self):
        targets = np.tile([0.25, -0.5], (10, 1)).astype(np.float32)
        observations, actions, info = collect(Fixture(), targets, EvaluationCase("test", 6))
        np.testing.assert_array_equal(observations[:, 0], [0, 1, 2, 3])
        np.testing.assert_array_equal(actions, targets[:4])
        self.assertEqual(info["controlled_ticks"], 4)
        self.assertEqual(info["reset_settling_ticks"], 120)
        self.assertIn("NOT an off-trajectory", info["teacher"])

    def test_warmup_is_replacement_for_twelve_ticks_not_appended(self):
        class Longer(Fixture):
            def step(self, action):
                obs, reward, terminated, _, info = super().step(action)
                return obs, reward, terminated, False, info
        case = EvaluationCase("left", 6, ((-0.5, 0.5),) * 3)
        targets = np.tile([0.25, -0.5], (16, 1)).astype(np.float32)
        _, actions, info = collect(Longer(), targets, case)
        np.testing.assert_array_equal(actions[:12], np.tile([-0.5, 0.5], (12, 1)))
        np.testing.assert_array_equal(actions[12:], targets[12:])
        self.assertEqual(info["controlled_ticks"], 16)

    def test_training_cases_do_not_reuse_evaluation_seeds(self):
        self.assertTrue(set(c.noise_seed for c in TRAINING_CASES if c.action_noise_std).isdisjoint(
            c.noise_seed for c in STANDARD_CASES if c.action_noise_std))
        self.assertTrue(set(c.reset_seed for c in TRAINING_CASES).isdisjoint(
            c.reset_seed for c in STANDARD_CASES))

    def test_safe_data_roundtrip_preserves_arrays_and_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "data"
            saved = save(output, **arrays(), metadata=metadata())
            loaded, record = load(output, provenance())
            self.assertEqual(saved, record)
            for key, value in arrays().items():
                np.testing.assert_array_equal(value, loaded[key])
            with self.assertRaisesRegex(ValueError, "new absolute"):
                save(output, **arrays(), metadata=metadata())

    def test_corruption_source_reward_and_privileged_data_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "data"
            save(output, **arrays(), metadata=metadata())
            original = json.loads((output / "manifest.json").read_text())
            for key, value in (("placement", True), ("ordinary_start", False), ("frame_skip", 4),
                               ("reward_contract", RewardConfig(profile="sparse").describe(1)),
                               ("data_sha256", "wrong")):
                record = {**original, key: value}
                (output / "manifest.json").write_text(json.dumps(record))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    load(output, provenance())
            (output / "manifest.json").write_text(json.dumps(original))
            changed = copy.deepcopy(provenance())
            changed["source_sha256"]["research/env.py"] = "changed"
            with self.assertRaisesRegex(ValueError, "environment/physics"):
                load(output, changed)

    def test_failed_episode_cannot_be_silently_marked_eligible(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "data"
            save(output, **arrays(), metadata=metadata(passed=False))
            with self.assertRaisesRegex(ValueError, "eligibility"):
                load(output, provenance())

    def test_forced_warmup_labels_are_excluded_without_dropping_physical_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "data"
            data, info = arrays(), metadata()
            info["episodes"][0]["warmup_ticks"] = 2
            data["eligible"][:2] = False
            save(output, **data, metadata=info)
            loaded, record = load(output, provenance())
            self.assertEqual(record["samples"], 4)
            self.assertEqual(record["eligible_samples"], 2)
            np.testing.assert_array_equal(loaded["eligible"], [False, False, True, True])

    def test_illegal_nonfinite_or_wrong_shape_arrays_are_refused(self):
        for key, value in (("actions", np.full((4, 2), 1.01, dtype=np.float32)),
                           ("observations", np.zeros((4, 89), dtype=np.float32)),
                           ("observations", np.full((4, 217), np.nan, dtype=np.float32)),
                           ("episode_ids", np.full(4, -1, dtype=np.int64))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_arrays(**{**arrays(), key: value})

    def test_exact_state_conflicts_do_not_claim_recovery_coverage(self):
        data = arrays()
        data["actions"][1] = [0.5, -0.5]
        summary = conflict_summary(data["observations"], data["actions"])
        self.assertEqual(summary["conflicting_groups"], 1)
        self.assertEqual(summary["max_normalized_target_range"], 0.5)
        self.assertIn("remain untested", summary["limit"])


if __name__ == "__main__":
    unittest.main()
