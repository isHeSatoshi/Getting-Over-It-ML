from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from tools.matched_host_inference import (
    ARRAYS, compare, contract, load_arrays, predict_singletons)


class MatchedInferenceTests(unittest.TestCase):
    def fixture(self):
        return {key: np.zeros(shape, dtype=np.float32) for key, shape in ARRAYS.items()}

    def test_fixture_load_preserves_float32_shapes_and_never_objects(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.npz"
            arrays = self.fixture()
            np.savez_compressed(path, **arrays)
            loaded = load_arrays(path)
            self.assertEqual(set(loaded), set(ARRAYS))
            for key in loaded:
                np.testing.assert_array_equal(loaded[key], arrays[key])

    def test_bad_fixture_headers_are_refused_before_numpy_allocation(self):
        for change in ("shape", "dtype", "object", "extra"):
            with tempfile.TemporaryDirectory() as folder:
                arrays = self.fixture()
                if change == "shape":
                    arrays["raw_observations"] = np.zeros((1, 217), dtype=np.float32)
                elif change == "dtype":
                    arrays["raw_observations"] = arrays["raw_observations"].astype(np.float64)
                elif change == "object":
                    arrays["raw_observations"] = np.empty((1800, 217), dtype=object)
                else:
                    arrays["unapproved"] = np.zeros(1)
                path = Path(folder) / "fixture.npz"
                np.savez_compressed(path, **arrays)
                with patch("tools.matched_host_inference.np.load") as loader:
                    with self.assertRaises(ValueError):
                        load_arrays(path)
                    loader.assert_not_called()

    def test_nan_and_illegal_archived_controls_refused(self):
        for value in (float("nan"), 1.01):
            with tempfile.TemporaryDirectory() as folder:
                arrays = self.fixture()
                arrays["recorded_applied_actions"][0, 0] = value
                path = Path(folder) / "fixture.npz"
                np.savez_compressed(path, **arrays)
                with self.assertRaises(ValueError):
                    load_arrays(path)

    def test_singleton_shape_determinism_and_order(self):
        class Policy:
            def predict(self, observation, deterministic):
                self.assertion = observation.shape == (1, 3) and deterministic is True
                return observation[:, :2] / 10, None
        policy = Policy()
        inputs = np.arange(15, dtype=np.float32).reshape(5, 3) / 2
        result = predict_singletons(policy, inputs, float("inf"))
        self.assertTrue(policy.assertion)
        np.testing.assert_array_equal(result, inputs[:, :2] / 10)

    def test_expired_deadline_prevents_any_policy_call(self):
        from unittest.mock import Mock
        policy = Mock()
        with self.assertRaises(ValueError):
            predict_singletons(policy, np.zeros((1, 217), dtype=np.float32), 0)
        policy.predict.assert_not_called()

    def test_first_difference_and_sample_count_are_not_goal_metrics(self):
        a = np.zeros((3, 2), dtype=np.float32)
        b = a.copy();b[1, 1] = .25
        result = compare(a, b)
        self.assertEqual(result["first_difference"]["sample"], 1)
        self.assertEqual(result["first_difference"]["element"], 1)
        self.assertEqual(result["differing_samples"], 1)
        self.assertEqual(result["maximum_absolute_difference"], .25)
        self.assertNotIn("success_rate", result)
        self.assertEqual(contract()["training_updates"], 0)
        self.assertEqual(contract()["control_ticks"], 0)

    def test_progress_callback_counts_actual_singleton_predictions(self):
        class Policy:
            def predict(self, observation, deterministic):
                return np.zeros((1, 2), dtype=np.float32), None
        calls = []
        predict_singletons(Policy(), np.zeros((3, 217), dtype=np.float32),
                           float("inf"), lambda index, action: calls.append(index))
        self.assertEqual(calls, [0, 1, 2])

    def test_monitor_never_labels_inference_as_physical_success(self):
        from tools.hf_research_status import inference_summary
        payload = {"controlled_ticks": 0, "reset_ticks": 0, "training_updates": 0,
                   "actual_inference_presentations": 3600, "status": "inference_complete_no_goal_promotion"}
        self.assertNotIn("success_rate", inference_summary(payload))
        for change in ({"controlled_ticks": 1}, {"training_updates": 1},
                       {"actual_inference_presentations": 3601}):
            with self.assertRaises(ValueError):
                inference_summary({**payload, **change})


if __name__ == "__main__":
    unittest.main()
