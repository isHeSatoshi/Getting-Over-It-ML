import unittest

from research.evaluation_cases import STANDARD_CASES
from research.imitation_study import plan
from research.study_metrics import benchmark_contract


class ImitationStudyTests(unittest.TestCase):
    def test_proposal_is_conditional_nonexecuting_and_keeps_evaluation_frozen(self):
        record = plan()
        self.assertIn("verified PAUSED", record["activation"])
        self.assertEqual(record["training_seeds"], [6, 7, 8])
        self.assertEqual(len(record["arms"]), 3)
        self.assertFalse(record["privileged_resets"])
        self.assertEqual(record["evaluation"]["cases"], [c.describe() for c in STANDARD_CASES])
        self.assertEqual(record["evaluation"]["benchmarks"], benchmark_contract(True))
        self.assertEqual(record["budget"]["cumulative_ceiling_usd"], 10)
        self.assertTrue(record["budget"]["new_reservation_required"])
        self.assertFalse(record["budget"]["interrupted_training_resume"])

    def test_work_units_and_teacher_limitations_are_explicit(self):
        record = plan()
        self.assertEqual(record["cloning"]["updates"] * record["cloning"]["batch_size"],
                         record["cloning"]["sample_presentations"])
        self.assertEqual(record["ppo"]["planned_policy_optimizer_calls"], 3840)
        self.assertIn("not a DAgger", record["data"]["recovery_limit"])
        self.assertIn("smoke-only", record["cloning"]["admission"])
        self.assertTrue(any("not equal" in warning for warning in record["caveats"]))


if __name__ == "__main__":
    unittest.main()
