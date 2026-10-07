"""Tests for the challenge contract: tiers, gates, and the hold detector.

The scoring rules are the whole point of the challenge, so they are tested
against hand-built traces rather than trusted.
"""
import unittest

import numpy as np

from challenge.env import RegionTracker
from challenge.tiers import (BASELINE, GATES, REGION_HOLD_TICKS, SCORING,
                             STANDARD_CASES, TIER0, TIER1, TIER2, TIER_REGIONS,
                             Region, gate_report, holdout_cases)


def tick(x, y, vx=0.0, vy=0.0, body=True, dead=False, success=False):
    return {"player_world_x": x, "player_world_y": y,
            "player_vx": vx, "player_vy": vy,
            "body_collision": body, "dead": dead, "success": success}


class RegionDefinitionTests(unittest.TestCase):
    def test_regions_are_well_formed(self):
        for region in TIER_REGIONS:
            self.assertTrue(region.name)
            self.assertLess(region.x_min, region.x_max)
            self.assertLess(region.y_min, region.y_max)
            self.assertGreater(region.hold_seconds, 0)

    def test_inverted_box_rejected(self):
        with self.assertRaises(ValueError):
            Region("bad", 10, 5, 0, 1)

    def test_inverted_y_rejected(self):
        with self.assertRaises(ValueError):
            Region("bad", 0, 10, 50, 10)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            Region("bad", 0, float("nan"), 0, 1)

    def test_bad_contact_fraction_rejected(self):
        with self.assertRaises(ValueError):
            Region("bad", 0, 10, 0, 10, min_body_contact_fraction=1.5)

    def test_baseline_terminal_is_tier1(self):
        x, y = BASELINE["terminal_position"]
        self.assertTrue(TIER1.x_min <= x <= TIER1.x_max)
        self.assertTrue(TIER1.y_min <= y <= TIER1.y_max)

    def test_spawn_is_tier0(self):
        # Measured on the reference runtime: spawn rests at (0, 21).
        self.assertTrue(TIER0.x_min <= 0.0 <= TIER0.x_max)
        self.assertTrue(TIER0.y_min <= 21.0 <= TIER0.y_max)


class RegionTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tracker = RegionTracker()

    def test_sustained_settle_passes(self):
        trace = [tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS)]
        summary = self.tracker.advance(trace)
        self.assertTrue(summary["region_success"][TIER0.name])

    def test_short_visit_does_not_pass(self):
        trace = [tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS - 1)]
        summary = self.tracker.advance(trace)
        self.assertFalse(summary["region_success"][TIER0.name])

    def test_moving_too_fast_does_not_pass(self):
        trace = [tick(0.0, 21.0, vx=9.0) for _ in range(REGION_HOLD_TICKS + 5)]
        summary = self.tracker.advance(trace)
        self.assertFalse(summary["region_success"][TIER0.name])

    def test_no_body_contact_does_not_pass(self):
        trace = [tick(0.0, 21.0, body=False) for _ in range(REGION_HOLD_TICKS + 5)]
        summary = self.tracker.advance(trace)
        self.assertFalse(summary["region_success"][TIER0.name])

    def test_death_resets_window(self):
        held = [tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS - 5)]
        died = [tick(0.0, 21.0, dead=True) for _ in range(3)]
        again = [tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS)]
        summary = self.tracker.advance(held + died + again)
        # The window is cleared by death, so the second run re-earns the hold.
        self.assertTrue(summary["region_success"][TIER0.name])
        self.assertIn("region_success_seconds", summary)

    def test_leaving_and_returning_requires_full_hold(self):
        inside = [tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS - 2)]
        outside = [tick(500.0, 21.0) for _ in range(5)]
        inside_again = [tick(0.0, 21.0) for _ in range(2)]
        summary = self.tracker.advance(inside + outside + inside_again)
        self.assertFalse(summary["region_success"][TIER0.name])

    def test_first_reach_recorded_even_without_hold(self):
        summary = self.tracker.advance([tick(0.0, 21.0) for _ in range(5)])
        self.assertIn(TIER0.name, summary["region_first_reach_seconds"])
        self.assertFalse(summary["region_success"][TIER0.name])

    def test_non_finite_telemetry_rejected(self):
        with self.assertRaises(ValueError):
            self.tracker.advance([tick(float("nan"), 21.0)])

    def test_reset_clears_state(self):
        self.tracker.advance([tick(0.0, 21.0) for _ in range(REGION_HOLD_TICKS)])
        self.tracker.reset()
        self.assertEqual(self.tracker.successes, {})


class GateTests(unittest.TestCase):
    def test_all_gates_pass(self):
        report = gate_report(1.0, 0.9, 0, True, 20)
        self.assertTrue(report["passed"])

    def test_holdout_gate_is_enforced(self):
        self.assertFalse(gate_report(1.0, 0.5, 0, True, 20)["passed"])

    def test_too_few_holdout_cases(self):
        self.assertFalse(gate_report(1.0, 0.9, 0, True, 5)["passed"])

    def test_tier0_gate_is_enforced(self):
        self.assertFalse(gate_report(0.2, 0.9, 0, True, 20)["passed"])

    def test_deaths_disqualify(self):
        self.assertFalse(gate_report(1.0, 0.9, 2, True, 20)["passed"])

    def test_summit_required_for_full_climb(self):
        self.assertFalse(gate_report(1.0, 0.9, 0, False, 20)["passed"])

    def test_gate_thresholds_match_constants(self):
        report = gate_report(GATES["holdout_pass_fraction"], GATES["holdout_pass_fraction"],
                             0, True, GATES["heldout_case_count"])
        self.assertTrue(report["checks"]["holdout_passed"])


class CaseTests(unittest.TestCase):
    def test_standard_cases_are_public(self):
        self.assertTrue(all(c.public for c in STANDARD_CASES))
        self.assertGreaterEqual(len(STANDARD_CASES), 9)

    def test_standard_cases_have_distinct_noise_seeds(self):
        noisy = [c.noise_seed for c in STANDARD_CASES if c.action_noise_std]
        self.assertEqual(len(noisy), len(set(noisy)))

    def test_holdout_cases_are_private_and_distinct(self):
        cases = holdout_cases()
        self.assertFalse(any(c.public for c in cases))
        self.assertEqual(len({c.name for c in cases}), len(cases))

    def test_holdout_does_not_overlap_standard(self):
        standard = {c.reset_seed for c in STANDARD_CASES}
        holdout = {c.reset_seed for c in holdout_cases()}
        self.assertFalse(standard & holdout)

    def test_warmups_are_legal_actions(self):
        for case in STANDARD_CASES:
            for action in case.warmup:
                self.assertEqual(len(action), 2)
                self.assertTrue(all(-1.0 <= v <= 1.0 for v in action))


class ScoringTests(unittest.TestCase):
    def test_transient_height_is_rejected(self):
        self.assertIn("transient maximum height (high-water mark without retained hold)",
                      SCORING["never_accepted_as_score"])


if __name__ == "__main__":
    unittest.main()
