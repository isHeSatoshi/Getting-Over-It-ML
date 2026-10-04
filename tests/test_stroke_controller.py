import unittest

import numpy as np

from research.env import BASE_FEATURES
from research.stroke_controller import StrokeController, contract


def fixture():
    observations = np.zeros((600, 217), np.float32)
    observations[:, 0] = np.arange(600, dtype=np.float32)/5500
    actions = np.column_stack((np.arange(600)/1000, np.full(600, -.5))).astype(np.float32)
    return observations, actions


class StrokeControllerTests(unittest.TestCase):
    def test_contract_is_explicit_causal_bounded_prior_not_teacher(self):
        record = contract()
        self.assertEqual(record["correction_norm_cap_pixels"], 16)
        self.assertEqual(record["maximum_phase"], 599)
        self.assertFalse(record["privileged_reset"])
        self.assertIn("No nearest-state", record["progress"])
        self.assertIn("not validated teacher", record["limit"])

    def test_recorded_inputs_have_exact_action_parity_and_reset(self):
        observations, actions = fixture()
        controller = StrokeController(observations, actions)
        for index in range(600):
            np.testing.assert_array_equal(controller.action(observations[index]), actions[index])
        self.assertEqual(controller.phase, 599)
        controller.reset()
        self.assertEqual((controller.phase, controller.calls), (0, 0))

    def test_no_elapsed_advancement_and_no_jump_to_distant_phase(self):
        observations, actions = fixture()
        controller = StrokeController(observations, actions)
        for _ in range(10):
            np.testing.assert_array_equal(controller.action(observations[0]), actions[0])
        self.assertEqual(controller.phase, 0)
        controller.action(observations[200])
        self.assertEqual(controller.phase, 1)

    def test_sideways_error_prevents_false_moving_stroke_completion(self):
        observations, actions = fixture()
        controller = StrokeController(observations, actions)
        controller.action(observations[0])
        offstate = observations[5].copy()
        offstate[BASE_FEATURES.index("altitude")] = 100/16000
        controller.action(offstate)
        self.assertEqual(controller.phase, 0)
        self.assertFalse(controller.last["observed_completion"])

    def test_stationary_stroke_requires_pose_and_speed_completion(self):
        observations, actions = fixture()
        observations[:] = 0
        controller = StrokeController(observations, actions)
        controller.action(observations[0])
        moving = observations[0].copy()
        moving[BASE_FEATURES.index("body_dx")] = 3/64
        controller.action(moving)
        self.assertEqual(controller.phase, 0)
        controller.action(observations[0])
        self.assertEqual(controller.phase, 1)

    def test_world_body_error_correction_has_right_sign_norm_cap_and_legal_range(self):
        observations, actions = fixture()
        controller = StrokeController(observations, actions)
        left = observations[0].copy()
        left[0] = -10/5500
        result = controller.action(left)
        self.assertAlmostEqual(float(result[0])*128, 10, places=5)
        far = observations[0].copy()
        far[:2] = (-1000/5500, -1000/16000)
        result = controller.action(far)
        self.assertAlmostEqual(np.linalg.norm(controller.last["pointer_correction_pixels"]), 16)
        self.assertEqual(result.dtype, np.float32)
        self.assertLessEqual(np.abs(result).max(), 1)

    def test_invalid_sources_inputs_and_work_budget_fail(self):
        observations, actions = fixture()
        for bad in (observations[:30], observations.astype(np.float64), np.full_like(observations, np.nan)):
            with self.assertRaises(ValueError):
                StrokeController(bad, actions)
        illegal = actions.copy()
        illegal[0, 1] = 2
        with self.assertRaises(ValueError):
            StrokeController(observations, illegal)
        controller = StrokeController(observations, actions)
        with self.assertRaises(ValueError):
            controller.action(observations[0].astype(np.float64))
        controller.calls = 1800
        with self.assertRaisesRegex(ValueError, "budget"):
            controller.action(observations[0])

    def test_reference_and_action_inputs_are_copied(self):
        observations, actions = fixture()
        controller = StrokeController(observations, actions)
        observations[:] = 99
        actions[:] = 99
        np.testing.assert_array_equal(controller.action(np.zeros(217, np.float32)), [0, -.5])

    def test_clock_ablation_keeps_prior_correction_and_bounds_contract_exact(self):
        original, timed = contract(), contract("timed_feedback")
        for key in ("version", "input", "progress"):
            original[key] = timed[key]
        self.assertEqual(original, timed)
        self.assertIn("not observed-state phase", timed["progress"])
        with self.assertRaises(ValueError):
            contract("silent_clock")

    def test_timed_feedback_uses_explicit_clock_even_if_pose_has_not_advanced(self):
        observations, actions = fixture()
        timed = StrokeController(observations, actions, "timed_feedback")
        for index in range(5):
            result = timed.action(observations[0])
            self.assertEqual(timed.phase, index)
            self.assertAlmostEqual(float(result[0])*128, float(actions[index, 0])*128+index, places=5)
        timed.reset()
        np.testing.assert_array_equal(timed.action(observations[0]), actions[0])
        self.assertEqual(timed.phase, 0)

    def test_timed_feedback_preserves_nominal_parity_and_caps_phase(self):
        observations, actions = fixture()
        timed = StrokeController(observations, actions, "timed_feedback")
        for index in range(600):
            np.testing.assert_array_equal(timed.action(observations[index]), actions[index])
        np.testing.assert_array_equal(timed.action(observations[599]), actions[599])
        self.assertEqual(timed.phase, 599)

    def test_timed_feedback_preserves_raw_input_work_and_correction_guards(self):
        observations, actions = fixture()
        with self.assertRaises(ValueError):
            StrokeController(observations, actions, "hidden_clock")
        timed = StrokeController(observations, actions, "timed_feedback")
        with self.assertRaises(ValueError):
            timed.action(observations[0].astype(np.float64))
        far = observations[0].copy()
        far[:2] = (-1000/5500, -1000/16000)
        result = timed.action(far)
        self.assertAlmostEqual(np.linalg.norm(timed.last["pointer_correction_pixels"]), 16)
        self.assertEqual(result.dtype, np.float32)
        self.assertLessEqual(np.abs(result).max(), 1)
        timed.calls = 1800
        with self.assertRaisesRegex(ValueError, "budget"):
            timed.action(observations[0])


if __name__ == "__main__":
    unittest.main()
