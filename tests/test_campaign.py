import unittest
from pathlib import Path
from unittest.mock import patch
from research.campaign import plan, command, execute, summarize_evaluation, promotion
from research.evaluation_cases import STANDARD_CASES
from research.milestones import FIRST_LEDGE
from research.resources import replay_buffer_bytes
import json
import tempfile
from research.campaign import aggregate


class CampaignTests(unittest.TestCase):
    def test_matrix_is_controlled_and_equal_budget(self):
        campaign = plan()
        self.assertEqual(len(campaign["runs"]), 9)
        self.assertEqual({r["steps"] for r in campaign["runs"]}, {98304})
        self.assertTrue(all(r["steps"] % 2048 == 0 for r in campaign["runs"]))
        self.assertFalse(campaign["promotion"]["large_scale_authorized"])

    def test_commands_are_remote_only(self):
        campaign = plan()
        args = command(campaign["runs"][0], campaign["fixed"], Path("D:/new/run"))
        self.assertIn("--remote-training", args)
        self.assertNotIn("--smoke", args)

    def test_desktop_campaign_refused_before_reading_files(self):
        with patch.dict("os.environ", {"FACTORY_DESKTOP_CDP_PORT": "123"}):
            with self.assertRaisesRegex(RuntimeError, "desktop"):
                execute(Path("D:/not-present"), 1)

    def test_duplicate_cases_cannot_pass_summary(self):
        with self.assertRaisesRegex(ValueError, "cases"):
            summarize_evaluation([])

    def test_replay_memory_estimate(self):
        self.assertEqual(replay_buffer_bytes(200000), 351200000)

    def test_complete_case_summary_uses_physical_milestone_not_reward(self):
        records = []
        for index, case in enumerate(STANDARD_CASES):
            final = {"milestone_success": {FIRST_LEDGE.name: index < 8}, "dead": False,
                     "retained_gain": 0, "reward_total": -100, "milestone_contract": [FIRST_LEDGE.__dict__]}
            records.append({"case": json.loads(json.dumps(case.describe())), "final": final,
                            "trace": [final], "decisions": 1})
        self.assertAlmostEqual(summarize_evaluation(records)["success_rate"], 8 / 9)

    def test_first_ledge_cannot_authorize_large_scale(self):
        rows = [{"variant": "sac_absolute", "seed": seed, "improvement": 0.8,
                 "after": {"success_rate": 0.9, "full_climb_success_rate": 0,
                           "nominal_full_climb_success": False}} for seed in (0, 1, 2)]
        followup, scale = promotion(rows, plan())
        self.assertEqual(followup, ["sac_absolute"])
        self.assertEqual(scale, [])

    def test_one_seed_or_duplicate_seeds_cannot_promote(self):
        row = {"variant": "sac_absolute", "seed": 0, "improvement": 0.8,
               "after": {"success_rate": 1, "full_climb_success_rate": 1,
                         "nominal_full_climb_success": True}}
        self.assertEqual(promotion([row], plan()), ([], []))
        self.assertEqual(promotion([row] * 3, plan()), ([], []))

    def test_full_reference_completion_required_for_scale(self):
        rows = [{"variant": "sac_absolute", "seed": seed, "improvement": 0.8,
                 "after": {"success_rate": 1, "full_climb_success_rate": 0.6,
                           "nominal_full_climb_success": True}} for seed in (0, 1, 2)]
        self.assertEqual(promotion(rows, plan()), (["sac_absolute"], ["sac_absolute"]))
        self.assertEqual(len(plan("followup", "sac_absolute")["runs"]), 3)
        self.assertEqual(len(plan("scale", "sac_absolute")["runs"]), 5)

    def test_missing_campaign_results_cannot_promote(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory / "campaign.json").write_text(json.dumps({"plan": plan(), "provenance": {}}), encoding="utf-8")
            result = aggregate(directory)
            self.assertEqual(result["decision"], "incomplete")
            self.assertEqual(len(result["missing_runs"]), 9)
            self.assertFalse(result["large_scale_authorized"])


if __name__ == "__main__":
    unittest.main()
