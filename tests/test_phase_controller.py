from types import SimpleNamespace
import unittest

import numpy as np

from research.env import BASE_FEATURES
from research.phase_controller import FEATURES, HISTORY_FEATURES, PhaseController, contract


def fixture():
    observations = np.zeros((600, 217), np.float32)
    observations[:, 0] = np.arange(600, dtype=np.float32)/1000
    actions = np.column_stack((np.arange(600)/1000, np.full(600, -.5))).astype(np.float32)
    rms = SimpleNamespace(mean=np.zeros(217), var=np.ones(217))
    return observations, actions, rms


class PhaseControllerTests(unittest.TestCase):
    def test_contract_is_feedback_prior_not_learning_or_offstate_oracle(self):
        record = contract()
        self.assertEqual(record["distance_features"], list(FEATURES))
        self.assertEqual(record["backtrack_rows"], 8)
        self.assertEqual(record["lookahead_rows"], 12)
        self.assertFalse(record["privileged_reset"])
        self.assertEqual(record["learning_updates"], 0)
        self.assertIn("not proof", record["limit"])

    def test_state_matched_phase_does_not_advance_with_elapsed_calls(self):
        obs, actions, rms = fixture()
        controller = PhaseController(obs, actions, rms)
        for _ in range(12):
            np.testing.assert_array_equal(controller.action(obs[0]), actions[0])
        self.assertEqual(controller.phase, 0)
        np.testing.assert_array_equal(controller.action(obs[5]), actions[5])
        self.assertEqual(controller.phase, 5)

    def test_phase_can_backtrack_but_cannot_jump_outside_window(self):
        obs, _, rms = fixture()
        controller = PhaseController(obs, fixture()[1], rms)
        controller.action(obs[12])
        self.assertEqual(controller.phase, 12)
        controller.action(obs[5])
        self.assertEqual(controller.phase, 5)
        controller.action(obs[200])
        self.assertEqual(controller.phase, 17)
        controller.action(obs[0])
        self.assertEqual(controller.phase, 9)

    def test_exact_recorded_states_select_matching_legal_actions_and_reset(self):
        obs, actions, rms = fixture()
        controller = PhaseController(obs, actions, rms)
        for index in range(600):
            np.testing.assert_array_equal(controller.action(obs[index]), actions[index])
        self.assertEqual(controller.phase, 599)
        controller.reset()
        self.assertEqual(controller.phase, 0)
        self.assertEqual(controller.calls, 0)

    def test_time_indexed_control_is_explicit_not_feedback(self):
        obs, actions, rms = fixture()
        controller = PhaseController(obs, actions, rms, "time_indexed")
        for index in range(5):
            np.testing.assert_array_equal(controller.action(obs[0]), actions[index])

    def test_bad_shapes_scales_actions_inputs_and_unbounded_work_fail(self):
        obs, actions, rms = fixture()
        for bad in (obs.astype(np.float64), obs[:20], np.full_like(obs, np.nan)):
            with self.assertRaises(ValueError):
                PhaseController(bad, actions, rms)
        bad = actions.copy()
        bad[0, 0] = 2
        with self.assertRaises(ValueError):
            PhaseController(obs, bad, rms)
        controller = PhaseController(obs, actions, rms)
        with self.assertRaises(ValueError):
            controller.action(obs[0].astype(np.float64))
        controller.calls = 1800
        with self.assertRaisesRegex(ValueError, "budget"):
            controller.action(obs[0])

    def test_control_history_is_the_only_changed_scientific_axis(self):
        original, history = contract(), contract("control_history")
        self.assertEqual(history["distance_features"], list(FEATURES + HISTORY_FEATURES))
        original["version"] = history["version"]
        original["distance_features"] = history["distance_features"]
        self.assertEqual(original, history)
        with self.assertRaises(ValueError):
            contract("arbitrary_features")

    def test_history_disambiguates_identical_kinematic_poses_without_time_advance(self):
        obs, actions, rms = fixture()
        obs[:, 0] = 0
        obs[:, BASE_FEATURES.index("pointer_x")] = np.arange(600, dtype=np.float32)/1000
        base = PhaseController(obs, actions, rms)
        history = PhaseController(obs, actions, rms, feature_set="control_history")
        np.testing.assert_array_equal(base.action(obs[5]), actions[0])
        np.testing.assert_array_equal(history.action(obs[5]), actions[5])
        for _ in range(10):
            np.testing.assert_array_equal(history.action(obs[5]), actions[5])
        self.assertEqual(history.phase, 5)

    def test_history_controller_has_same_raw_input_action_and_window_guards(self):
        obs, actions, rms = fixture()
        history = PhaseController(obs, actions, rms, feature_set="control_history")
        history.action(obs[200])
        self.assertEqual(history.phase, 12)
        history.action(obs[0])
        self.assertEqual(history.phase, 4)
        with self.assertRaises(ValueError):
            PhaseController(obs, actions, rms, feature_set="missing")
        with self.assertRaises(ValueError):
            history.action(obs[0].astype(np.float64))
        history.calls = 1800
        with self.assertRaisesRegex(ValueError, "budget"):
            history.action(obs[0])

    def test_history_exact_prior_action_parity_reset_and_frozen_scale(self):
        obs, actions, rms = fixture()
        original_mean, original_var = rms.mean.copy(), rms.var.copy()
        history = PhaseController(obs, actions, rms, feature_set="control_history")
        for index in range(600):
            np.testing.assert_array_equal(history.action(obs[index]), actions[index])
        np.testing.assert_array_equal(rms.mean, original_mean)
        np.testing.assert_array_equal(rms.var, original_var)
        history.reset()
        self.assertEqual(history.phase, 0)
        self.assertEqual(history.calls, 0)


if __name__ == "__main__":
    unittest.main()
