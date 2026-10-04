from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gymnasium as gym
import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.evaluation_cases import STANDARD_CASES, perturb
from research.reward import RewardConfig
from research.train import evaluate


class EvaluationFixture(gym.Env):
    """Synthetic evaluation orchestration only, not a policy-success test."""
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(2,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def __init__(self, frame_skip, horizon, terminal_ticks=None, invalid_ticks=None, **kwargs):
        self.frame_skip, self.horizon = frame_skip, horizon
        self.terminal_ticks, self.invalid_ticks = terminal_ticks, invalid_ticks
        self.actions, self.reset_seeds = [], []
        self.closed = False
        self.state = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.reset_seeds.append(seed)
        self.decision = 0
        self.state = {"tick": 120}
        return np.zeros(2, dtype=np.float32), {}

    def step(self, action):
        self.actions.append(np.asarray(action).copy())
        self.decision += 1
        ticks = self.frame_skip if self.terminal_ticks is None else self.terminal_ticks
        self.state = {"tick": self.state["tick"] + ticks}
        info = {"physics_ticks": ticks if self.invalid_ticks is None else self.invalid_ticks,
                "player_world_y": 100 + self.decision}
        return (np.zeros(2, dtype=np.float32), 0.0, self.terminal_ticks is not None,
                self.decision >= self.horizon, info)

    def close(self):
        self.closed = True


class FixturePolicy:
    def __init__(self, frame_skip=4, failure=False):
        self.gamma = RewardConfig().gamma(frame_skip)
        self.failure = failure
        self.calls = 0

    def predict(self, observation, deterministic=True):
        if self.failure:
            raise RuntimeError("Fixture policy failed")
        self.calls += 1
        return np.asarray([[self.calls / 100, -self.calls / 100]], dtype=np.float32), None


class TimingEvaluationTests(unittest.TestCase):
    def normalization(self, frame_skip=4):
        return SimpleNamespace(gamma=RewardConfig().gamma(frame_skip), norm_reward=False,
                               obs_rms=RunningMeanStd(shape=(2,)))

    def run_case(self, case, decisions=16, frame_skip=4, physical=False, **fixture):
        environments = []

        def create(**kwargs):
            env = EvaluationFixture(**kwargs, **fixture)
            environments.append(env)
            return env

        model = FixturePolicy(frame_skip)
        normalization = self.normalization(frame_skip)
        mean, variance = normalization.obs_rms.mean.copy(), normalization.obs_rms.var.copy()
        count = normalization.obs_rms.count
        with patch("research.train.RealGettingOverItEnv", side_effect=create):
            records = evaluate(model, normalization, None, "absolute", False, decisions, (),
                               cases=(case,), frame_skip=frame_skip, physical_case_clock=physical)
        np.testing.assert_array_equal(normalization.obs_rms.mean, mean)
        np.testing.assert_array_equal(normalization.obs_rms.var, variance)
        self.assertEqual(normalization.obs_rms.count, count)
        self.assertTrue(environments[0].closed)
        return records[0], environments[0]

    def test_default_four_tick_records_and_perturbations_are_unchanged(self):
        for case in STANDARD_CASES:
            with self.subTest(case=case.name):
                record, env = self.run_case(case)
                self.assertEqual(set(record), {"case", "seed", "final", "decisions", "trace"})
                self.assertEqual(env.frame_skip, 4)
                self.assertEqual(env.reset_seeds[0], case.reset_seed)
                rng = np.random.default_rng(case.noise_seed)
                for index, row in enumerate(record["trace"]):
                    predicted = np.asarray([row["action"]], dtype=np.float32)
                    expected = (np.asarray([case.warmup[index]], dtype=np.float32)
                                if index < len(case.warmup) else perturb(predicted, case, rng))
                    self.assertEqual(row["applied_action"], expected[0].tolist())

    def test_explicit_four_tick_clock_matches_all_legacy_case_traces(self):
        for case in STANDARD_CASES:
            with self.subTest(case=case.name):
                legacy, _ = self.run_case(case)
                timed, _ = self.run_case(case, physical=True)
                self.assertEqual(legacy["trace"], timed["trace"])
                self.assertEqual(legacy["final"], timed["final"])
                self.assertEqual(timed["controlled_physics_ticks"], 64)
                self.assertEqual(timed["reset_settling_physics_ticks"], 240)
                self.assertEqual(timed["timing_contract"]["requested_physics_ticks"], 64)

    def test_one_tick_warmup_holds_each_target_for_four_ticks(self):
        record, env = self.run_case(STANDARD_CASES[1], frame_skip=1, physical=True)
        self.assertEqual(env.frame_skip, 1)
        self.assertEqual([row["applied_action"] for row in record["trace"][:12]],
                         [[-0.5, 0.5]] * 12)
        self.assertEqual(record["trace"][12]["applied_action"], record["trace"][12]["action"])
        self.assertEqual(record["controlled_physics_ticks"], 16)

    def test_one_tick_predictions_change_while_noise_offset_is_held(self):
        record, _ = self.run_case(STANDARD_CASES[3], frame_skip=1, physical=True)
        offsets = np.asarray([np.asarray(row["applied_action"]) - row["action"]
                              for row in record["trace"]])
        for start in range(0, 16, 4):
            np.testing.assert_allclose(offsets[start:start + 4],
                                       np.tile(offsets[start], (4, 1)), rtol=0, atol=1e-8)
        self.assertFalse(np.array_equal(record["trace"][0]["action"], record["trace"][1]["action"]))

    def test_terminal_short_step_counts_real_ticks_and_uses_pre_reset_final_info(self):
        record, env = self.run_case(STANDARD_CASES[0], physical=True, terminal_ticks=2)
        self.assertEqual(record["decisions"], 1)
        self.assertEqual(record["controlled_physics_ticks"], 2)
        self.assertEqual(record["reset_settling_physics_ticks"], 240)
        self.assertEqual(record["final"]["player_world_y"], 101)
        self.assertEqual(env.state["tick"], 120)

    def test_timing_and_discount_mismatches_fail_before_environment_creation(self):
        for kwargs, normalization in (
            ({"frame_skip": 1}, self.normalization(1)),
            ({"frame_skip": 1, "physical_case_clock": True}, self.normalization(1)),
            ({"frame_skip": True}, self.normalization()),
            ({"frame_skip": 2, "physical_case_clock": True}, self.normalization()),
            ({"physical_case_clock": 1}, self.normalization()),
            ({"decisions": 0}, self.normalization()),
            ({}, self.normalization(1)),
        ):
            arguments = dict(decisions=16, seeds=(), cases=(STANDARD_CASES[0],))
            arguments.update(kwargs)
            with self.subTest(arguments=arguments):
                with patch("research.train.RealGettingOverItEnv") as create:
                    with self.assertRaises(ValueError):
                        evaluate(FixturePolicy(), normalization, None, "absolute", False, **arguments)
                    create.assert_not_called()

    def test_invalid_actual_tick_counts_fail_and_close_evaluation(self):
        for ticks in (0, 5, True, 1.5):
            env = EvaluationFixture(4, 16, invalid_ticks=ticks)
            with self.subTest(ticks=ticks):
                with patch("research.train.RealGettingOverItEnv", return_value=env):
                    with self.assertRaisesRegex(RuntimeError, "tick count"):
                        evaluate(FixturePolicy(), self.normalization(), None, "absolute", False,
                                 16, (), cases=(STANDARD_CASES[0],), physical_case_clock=True)
                self.assertTrue(env.closed)

    def test_failed_policy_still_closes_evaluation(self):
        env = EvaluationFixture(4, 16)
        with patch("research.train.RealGettingOverItEnv", return_value=env):
            with self.assertRaisesRegex(RuntimeError, "policy failed"):
                evaluate(FixturePolicy(failure=True), self.normalization(), None, "absolute", False,
                         16, (), cases=(STANDARD_CASES[0],), physical_case_clock=True)
        self.assertTrue(env.closed)


if __name__ == "__main__":
    unittest.main()
