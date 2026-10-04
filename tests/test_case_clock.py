import unittest

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.evaluation_cases import STANDARD_CASES, EvaluationCase, perturb


class PhysicalCaseClockTests(unittest.TestCase):
    def test_four_tick_actions_match_existing_evaluator_exactly(self):
        for case in STANDARD_CASES:
            with self.subTest(case=case.name):
                clock = PhysicalCaseClock(case)
                rng = np.random.default_rng(case.noise_seed)
                for index in range(16):
                    action = np.asarray([[index / 20, -index / 20]], dtype=np.float32)
                    expected = (np.asarray([case.warmup[index]], dtype=np.float32)
                                if index < len(case.warmup) else perturb(action, case, rng))
                    np.testing.assert_array_equal(clock.apply(action, index * 4), expected)

    def test_one_tick_and_four_tick_noise_have_same_physical_stream(self):
        case = STANDARD_CASES[3]
        one, four = PhysicalCaseClock(case), PhysicalCaseClock(case)
        action = np.zeros((1, 2), dtype=np.float32)
        fine = [one.apply(action, tick) for tick in range(24)]
        coarse = [four.apply(action, tick) for tick in range(0, 24, 4)]
        for tick in range(24):
            np.testing.assert_array_equal(fine[tick], coarse[tick // 4])

    def test_held_noise_does_not_hold_the_one_tick_policy_prediction(self):
        clock = PhysicalCaseClock(STANDARD_CASES[3])
        first = clock.apply(np.zeros((1, 2), dtype=np.float32), 0)
        second = clock.apply(np.full((1, 2), 0.25, dtype=np.float32), 1)
        np.testing.assert_allclose(second - first, 0.25, rtol=0, atol=3e-8)

    def test_warmup_is_twelve_physical_ticks_not_twelve_decisions(self):
        case = STANDARD_CASES[1]
        clock = PhysicalCaseClock(case)
        action = np.zeros((1, 2), dtype=np.float32)
        results = [clock.apply(action, tick).tolist() for tick in range(13)]
        self.assertEqual(results[:12], [[[-0.5, 0.5]]] * 12)
        self.assertEqual(results[12], [[0.0, 0.0]])

    def test_clock_rejects_repeated_regressed_or_skipped_ticks(self):
        for second in (0, -1, 8, True):
            clock = PhysicalCaseClock(STANDARD_CASES[3])
            clock.apply(np.zeros((1, 2)), 0)
            with self.subTest(second=second):
                with self.assertRaises(ValueError):
                    clock.apply(np.zeros((1, 2)), second)

    def test_noise_starts_after_legal_warmup(self):
        case = EvaluationCase("fixture", 1001, ((0.5, 0.5),), 0.02, 5)
        clock = PhysicalCaseClock(case)
        action = np.zeros((1, 2), dtype=np.float32)
        clock.apply(action, 0)
        expected = perturb(action, case, np.random.default_rng(5))
        np.testing.assert_array_equal(clock.apply(action, 4), expected)


if __name__ == "__main__":
    unittest.main()
