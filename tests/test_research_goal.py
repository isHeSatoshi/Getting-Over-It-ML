import copy
import unittest

from research.campaign import plan
from tools.research_goal_metrics import goal_metrics


class GoalMetricsTests(unittest.TestCase):
    def rows(self, rate=1.0, nominal=True):
        return [{"variant": "sac_absolute", "seed": seed,
                 "after": {"cases": 9, "success_rate": 1.0,
                           "full_climb_success_rate": rate,
                           "nominal_full_climb_success": nominal,
                           "falls": 0, "median_retained_gain": 16001.0}}
                for seed in (0, 1, 2)]

    def metrics(self, rows):
        return goal_metrics({"rows": rows, "missing_runs": []}, plan())

    def test_single_seed_cannot_establish_goal(self):
        result = self.metrics(self.rows()[:1])
        self.assertEqual(result["worst_seed_reference_completion_rate"], 0)
        self.assertFalse(result["candidate_goal_passed"])

    def test_first_ledge_only_does_not_pass_full_game_goal(self):
        result = self.metrics(self.rows(rate=0))
        self.assertFalse(result["candidate_goal_passed"])

    def test_worst_seed_not_average_determines_goal(self):
        rows = self.rows()
        rows[1]["after"]["full_climb_success_rate"] = 1 / 9
        result = self.metrics(rows)
        self.assertEqual(result["worst_seed_reference_completion_rate"], 1 / 9)
        self.assertFalse(result["candidate_goal_passed"])

    def test_nominal_completion_is_required_for_every_seed(self):
        self.assertFalse(self.metrics(self.rows(nominal=False))["candidate_goal_passed"])

    def test_success_is_only_candidate_until_independent_checks(self):
        result = self.metrics(self.rows(rate=8 / 9))
        self.assertTrue(result["candidate_goal_passed"])
        self.assertFalse(result["final_goal_verified"])

    def test_duplicate_training_seeds_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.metrics([self.rows()[0], copy.deepcopy(self.rows()[0])])

    def test_invalid_success_fractions_fail(self):
        for value in (float("nan"), float("inf"), -1, 2):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "fraction"):
                    self.metrics(self.rows(rate=value))

    def test_missing_evaluation_cases_cannot_establish_goal(self):
        rows = self.rows()
        rows[0]["after"]["cases"] = 1
        self.assertFalse(self.metrics(rows)["candidate_goal_passed"])


if __name__ == "__main__":
    unittest.main()
