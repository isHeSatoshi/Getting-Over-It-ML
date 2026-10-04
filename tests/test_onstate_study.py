import unittest

from research.demonstrations import TRAINING_CASES
from research.evaluation_cases import STANDARD_CASES
from research.onstate_study import ARMS, SEEDS, VALIDATION_CASES, plan
from research.study_metrics import benchmark_contract


class OnStateStudyTests(unittest.TestCase):
    def test_frozen_matched_data_comparison_is_not_an_admission(self):
        record = plan()
        self.assertEqual(record["training_seeds"], [9, 10, 11])
        self.assertEqual(record["arms"], list(ARMS))
        self.assertEqual(len(record["run_order"]), 6)
        self.assertEqual(record["initialization"]["architecture"], [256, 256])
        self.assertEqual(record["cloning"]["updates"] * record["cloning"]["batch_size"], 512000)
        self.assertEqual(record["cloning"]["rl_transitions"], 0)
        self.assertIn("Proposal only", record["activation"])
        self.assertIn("smoke-only", record["cloning"]["admission"])
        self.assertFalse(record["gate"]["full_goal_verified_from_this_comparison"])
        self.assertEqual(record["gate"]["minimum_central_holds_per_seed"], 8)
        self.assertEqual(record["evaluation"]["benchmarks"], benchmark_contract(True))

    def test_source_weights_work_limits_and_ambiguity_are_explicit(self):
        record = plan()
        self.assertEqual(record["cloning"]["original_arm_per_batch"],
                         {"original": 256, "logged_success": 0})
        self.assertEqual(record["cloning"]["augmented_arm_per_batch"],
                         {"original": 192, "logged_success": 64})
        self.assertIn("Retain all", record["data"]["ambiguity"])
        self.assertIn("not a", record["data"]["selection"])
        self.assertIn("never inverse", record["data"]["raw_source"])
        self.assertEqual(record["budget"]["maximum_control_ticks"], 108 * 1800)
        self.assertEqual(record["budget"]["maximum_reset_ticks"], 108 * 240)
        self.assertEqual(record["budget"]["maximum_session_seconds"], 7200)
        self.assertEqual(record["budget"]["cumulative_ceiling_usd"], 10)
        self.assertFalse(record["budget"]["interrupted_training_resume"])

    def test_new_validation_streams_never_include_selected8105_or_old_demos(self):
        old_noise = {case.noise_seed for case in (*STANDARD_CASES, *TRAINING_CASES)
                     if case.action_noise_std}
        new_noise = {case.noise_seed for case in VALIDATION_CASES if case.action_noise_std}
        self.assertEqual(new_noise, set(range(10100, 10106)))
        self.assertFalse(old_noise & new_noise)
        self.assertEqual(len(VALIDATION_CASES), 9)
        self.assertEqual(len(SEEDS), 3)
        self.assertEqual(VALIDATION_CASES[1].warmup, ((-0.625, 0.375),) * 3)
        self.assertNotEqual(VALIDATION_CASES[1].warmup, STANDARD_CASES[1].warmup)
        self.assertIn("never counted", plan()["evaluation"]["old_noise8105"])


if __name__ == "__main__":
    unittest.main()
