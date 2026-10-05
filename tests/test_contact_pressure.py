import unittest

import numpy as np

from research.contact_pressure import (AnchorPressureStep, ContactTargetPhase, MIN_PRESSURE_REACH,
                                      contract, hammer, pressure_distance)
from research.hammer_target import HammerTargetPhase
from tests.test_hammer_target import raw


def post(body=(270., 32.), tip=(284., 65.), query=0, travel=0):
    result = raw(body, tip)
    result[22], result[19] = query, travel/64
    return result


class ContactPressureTests(unittest.TestCase):
    def phase(self):
        phase, pre = ContactTargetPhase([292., 70.]), post()
        phase.bootstrap(np.zeros(2, np.float32), pre)
        return phase, pre

    def transition(self, phase, pre, query, travel=0, tip=(284., 65.)):
        action = phase.action(pre)
        actual = post(tip=tip, query=query, travel=travel)
        actual[13:15] = action
        return actual, phase.observe(actual)

    def test_contract_distinguishes_query_proxy_and_unchanged_geometric_target(self):
        record = contract()
        self.assertTrue(record["query_proxy_not_endpoint_plant_or_bodyauthority"])
        self.assertEqual((record["maximum_steps"], record["target"]["tolerance_pixels"]), (30, 1))
        self.assertFalse(record["teacher_data_admission"])

    def test_two_actual_post_queries_acquire_far_from_goal(self):
        phase, pre = self.phase()
        pre, result = self.transition(phase, pre, 1, 2)
        self.assertEqual((result["phase"], result["query_streak"]), ("active", 1))
        pre, result = self.transition(phase, pre, 1, 1)
        self.assertEqual(result["phase"], "acquired")
        np.testing.assert_array_equal(phase.anchor, hammer(pre))
        self.assertGreater(phase.target.last_error, 1)
        with self.assertRaises(ValueError):
            phase.action(pre)
        with self.assertRaises(ValueError):
            phase.observe(pre)

    def test_query_gap_or_travel3_resets_streak(self):
        for query, travel in ((0, 0), (1, 3)):
            phase, pre = self.phase()
            pre, _ = self.transition(phase, pre, 1)
            pre, result = self.transition(phase, pre, query, travel)
            self.assertEqual(result["query_streak"], 0)
            pre, result = self.transition(phase, pre, 1)
            self.assertEqual(result["phase"], "active")
            _, result = self.transition(phase, pre, 1)
            self.assertEqual(result["phase"], "acquired")

    def test_free_geometric_completion_fails_without_extra_contact_ticks(self):
        phase, pre = self.phase()
        pre, result = self.transition(phase, pre, 0, tip=(292., 70.))
        self.assertEqual(result["reason"], "free_geometric_completion")
        with self.assertRaises(ValueError):
            phase.action(pre)

    def test_timeout_and_terminal_have_failure_priority(self):
        phase, pre = self.phase()
        for i in range(30):
            pre, result = self.transition(phase, pre, int(i >= 28))
        self.assertEqual((result["phase"], result["reason"]), ("failed", "target_timeout"))
        phase, pre = self.phase()
        pre, _ = self.transition(phase, pre, 1)
        action = phase.action(pre)
        terminal = post(body=(270., -181.), query=1)
        terminal[13:15] = action
        self.assertEqual(phase.observe(terminal)["reason"], "terminal_altitude")

    def test_pairing_raw_and_prepost_guards(self):
        phase, pre = self.phase()
        with self.assertRaises(ValueError):
            phase.observe(pre)
        phase.action(pre)
        with self.assertRaises(ValueError):
            phase.action(pre)
        phase.observe(pre)
        with self.assertRaises(ValueError):
            phase.action(post(body=(269., 32.)))
        for invalid in (pre.astype(np.float64), np.zeros(216, np.float32)):
            with self.assertRaises(ValueError):
                phase.action(invalid)
        invalid = pre.copy()
        invalid[22] = .5
        with self.assertRaises(ValueError):
            phase.action(invalid)

    def test_illegal_target_is_permanent_failure(self):
        phase, pre = ContactTargetPhase([1000., 70.]), post()
        phase.bootstrap(np.zeros(2, np.float32), pre)
        with self.assertRaises(ValueError):
            phase.action(pre)
        self.assertEqual(phase.phase, "failed")

    def test_anchor_and_summary_are_copied(self):
        phase, pre = self.phase()
        pre, _ = self.transition(phase, pre, 1)
        pre, result = self.transition(phase, pre, 1)
        anchor = phase.anchor.copy()
        pre[:] = 0
        result["anchor"][0] = 0
        np.testing.assert_array_equal(phase.anchor, anchor)

    def step(self, pressure=True):
        pre = post()
        anchor = hammer(pre)
        step = AnchorPressureStep(anchor, [280., 48.], pressure)
        step.bootstrap(np.zeros(2, np.float32), pre)
        return step, pre

    def test_first_inner_boundary_not_end_inside_or_beyond_circle(self):
        length = pressure_distance(np.array([40., 0.]), np.array([-1., 0.]))
        self.assertAlmostEqual(length, 40-MIN_PRESSURE_REACH)
        # A long ray could leave the forbidden inner disk again; stop at first entry.
        length = pressure_distance(np.array([30., 0.]), np.array([-1., 0.]))
        self.assertAlmostEqual(length, 30-MIN_PRESSURE_REACH)

    def test_outer_bound_and_norm16_max(self):
        self.assertAlmostEqual(pressure_distance(np.array([100., 0.]), np.array([1., 0.])), 2)
        self.assertEqual(pressure_distance(np.array([50., 0.]), np.array([0., 1.])), 16)
        with self.assertRaises(ValueError):
            pressure_distance(np.array([26., 0.]), np.array([-1., 0.]))
        with self.assertRaises(ValueError):
            pressure_distance(np.array([102., 0.]), np.array([1., 0.]))

    def test_anchor_pressure_shortens_analytically_with_same_anchor(self):
        step, pre = self.step()
        action = step.action(pre)
        self.assertTrue(0 < step.last["pressure_distance_pixels"] < 16)
        self.assertAlmostEqual(step.last["requested_reach"], MIN_PRESSURE_REACH, places=9)
        self.assertEqual(action.dtype, np.float32)
        self.assertTrue(np.abs(action).max() <= 1)
        baseline, _ = self.step(False)
        baseline.action(pre)
        self.assertEqual(baseline.last["delta"], [0., 0.])
        self.assertEqual(step.last["anchor"], baseline.last["anchor"])

    def test_one_pressure_action_then_one_observe_no_rearm(self):
        step, pre = self.step()
        action = step.action(pre)
        action[:] = 1
        with self.assertRaises(ValueError):
            step.action(pre)
        actual = pre.copy()
        actual[13:15] = step.issued_command+[2/128, -1/128]
        step.observe(actual)
        np.testing.assert_allclose(step.cursor_estimate, [2, -1], atol=1e-5)
        with self.assertRaises(ValueError):
            step.observe(actual)
        with self.assertRaises(ValueError):
            step.bootstrap(np.zeros(2, np.float32), actual)

    def test_pressure_requires_exact_actual_anchor_history_and_pre(self):
        step, pre = self.step()
        with self.assertRaises(ValueError):
            step.action(post(body=(269., 32.)))
        with self.assertRaises(ValueError):
            step.bootstrap(np.zeros(2, np.float32), pre)
        bad = AnchorPressureStep([300., 70.], [280., 48.], True)
        with self.assertRaises(ValueError):
            bad.bootstrap(np.zeros(2, np.float32), pre)
        with self.assertRaises(ValueError):
            AnchorPressureStep(hammer(pre), [280., 48.], 1)

    def test_pressure_no_direction_or_illegal_cursor_fails_without_clipping(self):
        pre = post()
        step = AnchorPressureStep(hammer(pre), HammerTargetPhase.body(pre), True)
        step.bootstrap(np.zeros(2, np.float32), pre)
        with self.assertRaises(ValueError):
            step.action(pre)
        self.assertEqual(step.phase, "failed")
        step = AnchorPressureStep(hammer(pre), [280., 48.], False)
        pre[13] = 2
        step.bootstrap(np.zeros(2, np.float32), pre)
        with self.assertRaises(ValueError):
            step.action(pre)
        self.assertEqual(step.phase, "failed")

if __name__ == "__main__":
    unittest.main()
