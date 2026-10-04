import unittest

from research.timing_study import plan


class TimingStudyTests(unittest.TestCase):
    def test_equal_physical_exposure_and_optimizer_call_count(self):
        study = plan()
        one, four = study["arms"]
        self.assertEqual(one["transitions"], four["transitions"] * 4)
        self.assertEqual(one["transitions"] * one["frame_skip"],
                         four["transitions"] * four["frame_skip"])
        self.assertEqual(one["planned_optimizer_calls"], 3840)
        self.assertEqual(one["planned_optimizer_calls"], four["planned_optimizer_calls"])
        self.assertEqual(one["batch_size"], four["batch_size"] * 4)

    def test_discount_and_gae_have_equal_physical_decay(self):
        one, four = plan()["arms"]
        self.assertAlmostEqual(one["gamma"] ** 4, four["gamma"])
        self.assertAlmostEqual(one["gae_lambda"] ** 4, four["gae_lambda"])

    def test_episode_and_evaluation_durations_match(self):
        for arm in plan()["arms"]:
            self.assertEqual(arm["episode_decisions"] * arm["frame_skip"], 12000)
            self.assertEqual(arm["evaluation_decisions"] * arm["frame_skip"], 1800)
            self.assertEqual(arm["transitions"] % arm["rollout_steps"], 0)

    def test_cases_preserve_physical_warmup_and_noise_time(self):
        cases = plan()["cases"]
        self.assertEqual(len(cases), 9)
        self.assertEqual(next(c for c in cases if c["name"] == "hammer_left")["warmup_total_ticks"], 12)
        self.assertTrue(all(c["noise_hold_ticks"] == 4 for c in cases))

    def test_preparation_cannot_authorize_or_launch_a_study(self):
        study = plan()
        self.assertEqual(study["state"], "prepared_only_not_executable")
        self.assertEqual(study["training_seeds"], [3, 4, 5])
        self.assertFalse(study["fixed"]["privileged_resets"])
        self.assertTrue(study["benchmarks"]["requires_secondary_physical_calibration_before_activation"])


if __name__ == "__main__":
    unittest.main()
