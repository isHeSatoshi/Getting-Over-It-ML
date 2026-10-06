from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from research.goal_campaign import reserve, approve_training
from research.goal_execution import CHECKS
from tests.test_goal_worker import admission_fixture


class GoalCampaignTests(unittest.TestCase):
    def test_reservation_is_fresh_capped_and_does_not_modify_original_ledger(self):
        ledger = {"currency": "USD", "operating_ceiling": 10., "batches": [
            {"session": "old", "verified_end_epoch": 1, "estimated_elapsed_compute_cost_upper_bound": .4564}]}
        original = deepcopy(ledger)
        new = reserve(ledger, "goal-new-1", 100, 36100, "a"*40, .03)
        self.assertEqual(ledger, original)
        self.assertEqual(new["batches"][-1]["maximum_estimated_compute_cost"], .30)
        with self.assertRaises(ValueError):
            reserve(new, "goal-new-2", 100, 36100, "a"*40, .03)
        with self.assertRaises(ValueError):
            reserve(ledger, "goal-new-1", 100, 36101, "a"*40, .03)

    def test_failed_missing_or_wrong_session_preflight_cannot_approve_training(self):
        ticket, ledger, environment = admission_fixture()
        current = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
        previous = {**deepcopy(ticket["preflight"]), "study_kind": "goal"}
        result = approve_training(current, previous, "b"*40)
        self.assertIsNone(result["ticket"]["context_revision"])
        previous["checks"]["goal_pipeline"] = False
        with self.assertRaises(ValueError):
            approve_training(current, previous, "b"*40)
        previous["checks"]["goal_pipeline"] = True
        del previous["checks"]["benchmark"]
        with self.assertRaises(ValueError):
            approve_training(current, previous, "b"*40)

    def test_goal_checkpoint_schema_not_old217_or_residual222(self):
        from research.goal_env import schema
        from research.goal_study import plan
        self.assertEqual(schema()["dimension"], 620)
        self.assertEqual(plan()["seeds"], [21])
        self.assertEqual(plan()["scale_probe"]["kind"], "demo-seeded-exploration")
        self.assertEqual(plan()["scale_probe"]["baseline_learner_transitions"], 160000)
        self.assertEqual(plan()["demo_seed"]["burst_ticks"], 60)
        self.assertEqual(plan()["max_sac_cycles_per_seed"], (480000-4096)//2)
        self.assertFalse(plan()["pilot_gate"]["prefix_or_playback_in_evaluation"])


if __name__ == "__main__":
    unittest.main()
