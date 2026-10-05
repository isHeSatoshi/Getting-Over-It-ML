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


if __name__ == "__main__":
    unittest.main()
