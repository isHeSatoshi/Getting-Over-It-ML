import unittest

import numpy as np

from research.hammer_target import HammerTargetPhase, contract


def raw(body=(270., 32.), hammer=(190., -8.)):
    observation = np.zeros(217, dtype=np.float32)
    observation[:2] = np.asarray(body)/[5500, 16000]
    observation[6:8] = (np.asarray(hammer)-body)/102
    return observation


class HammerTargetTests(unittest.TestCase):
    def test_fixed_contract_not_query_or_body_completion(self):
        record = contract()
        self.assertEqual((record["maximum_steps"], record["tolerance_pixels"]), (30, 1))
        self.assertFalse(record["query_release_is_completion"])
        self.assertFalse(record["body_alignment_is_demonstrated"])
        self.assertFalse(record["teacher_data_admission"])

    def test_pointer_recomputed_from_actual_body_and_float32(self):
        phase = HammerTargetPhase([187., 4.])
        pre = raw()
        action = phase.action(pre)
        expected = ((phase.goal-phase.body(pre)-[0, 20])/128).astype(np.float32)
        np.testing.assert_array_equal(action, expected)
        post = raw(body=(269., 32.))
        phase.observe(post)
        self.assertFalse(phase.summary()["finished"])
        self.assertNotEqual(phase.action(post)[0], action[0])

    def test_release_flag_does_not_complete_but_actual_post_goal_does(self):
        phase = HammerTargetPhase([187., 4.])
        pre = raw()
        phase.action(pre)
        phase.observe(pre)
        self.assertEqual(phase.phase, "active")
        phase.action(pre)
        phase.observe(raw(hammer=(187., 4.)))
        self.assertEqual(phase.phase, "succeeded")
        with self.assertRaises(ValueError):
            phase.action(pre)

    def test_exact_pairs_and_prepost_link(self):
        phase, pre = HammerTargetPhase([187., 4.]), raw()
        with self.assertRaises(ValueError):
            phase.observe(pre)
        phase.action(pre)
        with self.assertRaises(ValueError):
            phase.action(pre)
        phase.observe(pre)
        with self.assertRaises(ValueError):
            phase.action(raw(body=(269., 32.)))

    def test_timeout30_is_permanent_no_second_attempt(self):
        phase, pre = HammerTargetPhase([187., 4.]), raw()
        for _ in range(30):
            phase.action(pre)
            phase.observe(pre)
        self.assertEqual((phase.steps, phase.phase, phase.reason), (30, "failed", "target_timeout"))
        with self.assertRaises(ValueError):
            phase.action(pre)
        with self.assertRaises(ValueError):
            phase.observe(pre)

    def test_illegal_goal_fails_not_clipped_or_renewed(self):
        for goal in ([1000., 4.], [270., 32.], [270., -90.]):
            phase = HammerTargetPhase(goal)
            with self.assertRaises(ValueError):
                phase.action(raw())
            self.assertEqual(phase.reason, "illegal_target")
            self.assertFalse(phase.pending)
            with self.assertRaises(ValueError):
                phase.action(raw())

    def test_invalid_goal_and_raw_inputs_rejected(self):
        for goal in ([1.], [float("nan"), 4.]):
            with self.assertRaises(ValueError):
                HammerTargetPhase(goal)
        phase = HammerTargetPhase([187., 4.])
        for observation in (raw().astype(np.float64), np.zeros(216, np.float32), np.full(217, np.nan, np.float32)):
            with self.assertRaises(ValueError):
                phase.action(observation)

    def test_terminal_altitude_fails_before_qualification(self):
        phase, pre = HammerTargetPhase([187., 4.]), raw()
        phase.action(pre)
        phase.observe(raw(body=(270., -181.)))
        self.assertEqual(phase.reason, "terminal_altitude")

    def test_feedback_contract_does_not_change_default(self):
        default, feedback = contract(), contract(True)
        self.assertNotEqual(default["version"], feedback["version"])
        self.assertEqual(default["maximum_steps"], feedback["maximum_steps"])
        self.assertEqual(default["tolerance_pixels"], feedback["tolerance_pixels"])
        self.assertNotIn("estimate_update", default)
        self.assertIn("OWN", feedback["estimate_update"])
        for value in (1, "feedback", None):
            with self.assertRaises(ValueError):
                HammerTargetPhase([187., 4.], value)

    def test_feedback_requires_exactly_one_bootstrap_with_valid_history(self):
        pre, command = raw(), np.asarray([-.5, -.25], np.float32)
        phase = HammerTargetPhase([187., 4.], True)
        with self.assertRaises(ValueError):
            phase.action(pre)
        for invalid in (command.astype(np.float64), np.asarray([2., 0.], np.float32), np.zeros(3, np.float32)):
            with self.assertRaises(ValueError):
                phase.bootstrap(invalid, pre)
        phase.bootstrap(command, pre)
        with self.assertRaises(ValueError):
            phase.bootstrap(command, pre)
        with self.assertRaises(ValueError):
            phase.action(raw(body=(269., 32.)))
        with self.assertRaises(ValueError):
            HammerTargetPhase([187., 4.]).bootstrap(command, pre)

    def test_feedback_subtracts_past_cursor_and_updates_from_issued_not_desired(self):
        phase, pre = HammerTargetPhase([187., 4.], True), raw()
        previous = np.asarray([-.5, -.25], np.float32)
        pre[13:15] = previous+np.asarray([2/128, -1/128], np.float32)
        phase.bootstrap(previous, pre)
        base = ((phase.goal-phase.body(pre)-[0, 20])/128).astype(np.float32)
        expected = ((base.astype(np.float64)*128-[2, -1])/128).astype(np.float32)
        action = phase.action(pre)
        np.testing.assert_array_equal(action, expected)
        post = pre.copy()
        post[13:15] = action+np.asarray([3/128, 1/128], np.float32)
        phase.observe(post)
        np.testing.assert_allclose(phase.cursor_estimate, [3, 1], rtol=0, atol=1e-5)
        next_expected = ((base.astype(np.float64)*128-phase.cursor_estimate)/128).astype(np.float32)
        np.testing.assert_array_equal(phase.action(post), next_expected)

    def test_feedback_bootstrap_and_returned_command_are_copied(self):
        phase, pre, command = HammerTargetPhase([187., 4.], True), raw(), np.asarray([0., 0.], np.float32)
        phase.bootstrap(command, pre)
        command[:] = 1
        pre[13] = .1
        correct_pre = phase.previous_post.copy()
        action = phase.action(correct_pre)
        issued = action.copy()
        action[:] = 0
        post = correct_pre.copy()
        post[13:15] = issued
        phase.observe(post)
        np.testing.assert_array_equal(phase.cursor_estimate, [0, 0])

    def test_feedback_illegal_compensation_fails_without_clipping_or_restart(self):
        phase, pre = HammerTargetPhase([187., 4.], True), raw()
        pre[13] = 1
        phase.bootstrap(np.asarray([-1., 0.], np.float32), pre)
        with self.assertRaises(ValueError):
            phase.action(pre)
        self.assertEqual(phase.reason, "illegal_cursor_compensation")
        self.assertFalse(phase.pending)
        with self.assertRaises(ValueError):
            phase.bootstrap(np.zeros(2, np.float32), pre)

    def test_feedback_timeout_and_terminal_qualification_stay_unchanged(self):
        phase, pre = HammerTargetPhase([187., 4.], True), raw()
        pre[13:15] = [-83/128, -48/128]
        phase.bootstrap(pre[13:15].copy(), pre)
        for _ in range(30):
            action = phase.action(pre)
            post = pre.copy()
            post[13:15] = action
            phase.observe(post)
            pre = post
        self.assertEqual((phase.phase, phase.steps, phase.reason), ("failed", 30, "target_timeout"))
        with self.assertRaises(ValueError):
            phase.action(pre)


if __name__ == "__main__":
    unittest.main()
