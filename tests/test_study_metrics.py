from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gymnasium as gym
import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.evaluation_cases import STANDARD_CASES
from research.milestones import FIRST_LEDGE, MilestoneTracker
from research.policy_fidelity import compare_rollouts, rollout
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract, enable_platform_support
from research.timing_probe import PLATFORM_SUPPORT
from research.train import evaluate


class MetricFixture(gym.Env):
    """Synthetic detector integration, not reaching/holding a real platform."""
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(2,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def __init__(self, frame_skip=4, horizon=100, **kwargs):
        self.frame_skip, self.horizon = frame_skip, horizon
        self.reward_config = RewardConfig()
        self.gamma = self.reward_config.gamma(frame_skip)
        self.milestones = MilestoneTracker()
        self.state = None
        self.actions = []
        self.closed = False

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = {"tick": 120}
        self.decision = 0
        self.milestones.reset()
        return np.zeros(2, dtype=np.float32), self.milestones.summary()

    def step(self, action):
        self.actions.append(np.asarray(action).copy())
        self.decision += 1
        trace = []
        for _ in range(self.frame_skip):
            self.state = {"tick": self.state["tick"] + 1, "player_world_x": 290,
                          "player_world_y": 104, "player_vx": 0, "player_vy": 0,
                          "body_collision": True, "dead": False, "success": False}
            trace.append(self.state)
        info = {"physics_ticks": len(trace), **self.milestones.advance(trace)}
        return np.zeros(2, dtype=np.float32), 0.0, False, self.decision >= self.horizon, info

    def close(self):
        self.closed = True


class ZeroPolicy:
    def __init__(self, repeat=4):
        self.gamma = RewardConfig().gamma(repeat)

    def predict(self, observation, deterministic=True):
        return np.zeros((1, 2), dtype=np.float32), None


class StudyMetricTests(unittest.TestCase):
    def test_contract_retains_frozen_v1_and_only_adds_declared_support(self):
        self.assertEqual(benchmark_contract(), [FIRST_LEDGE.__dict__])
        self.assertEqual(benchmark_contract(True), [FIRST_LEDGE.__dict__, PLATFORM_SUPPORT.__dict__])
        with self.assertRaises(ValueError):
            benchmark_contract(1)

    def test_reconfiguration_after_reset_or_with_changed_tracker_is_refused(self):
        env = MetricFixture()
        env.reset()
        with self.assertRaisesRegex(ValueError, "first reset"):
            enable_platform_support(env)
        env = MetricFixture()
        env.milestones = MilestoneTracker((PLATFORM_SUPPORT,))
        with self.assertRaisesRegex(ValueError, "default v1"):
            enable_platform_support(env)

    def test_extra_diagnostic_changes_only_milestone_info_not_actions_rewards_or_observations(self):
        plain, extra = MetricFixture(), enable_platform_support(MetricFixture())
        a, _ = plain.reset(seed=7)
        b, _ = extra.reset(seed=7)
        np.testing.assert_array_equal(a, b)
        for _ in range(24):
            a, b = plain.step([0.25, -0.5]), extra.step([0.25, -0.5])
            np.testing.assert_array_equal(a[0], b[0])
            self.assertEqual(a[1:4], b[1:4])
            for key in ("milestone_success", "milestone_first_reach_seconds",
                        "milestone_success_seconds", "milestone_best_hold_seconds"):
                self.assertEqual(a[4][key][FIRST_LEDGE.name], b[4][key][FIRST_LEDGE.name])
        self.assertFalse(b[4]["milestone_success"][FIRST_LEDGE.name])
        self.assertTrue(b[4]["milestone_success"][PLATFORM_SUPPORT.name])
        np.testing.assert_array_equal(plain.actions, extra.actions)

    def test_evaluator_opt_in_keeps_both_metrics_and_terminal_pre_reset_result(self):
        for repeat in (1, 4):
            normalization = SimpleNamespace(gamma=RewardConfig().gamma(repeat),
                                           norm_reward=False, obs_rms=RunningMeanStd(shape=(2,)))
            env = MetricFixture(frame_skip=repeat, horizon=100 // repeat)
            with patch("research.train.RealGettingOverItEnv", return_value=env):
                records = evaluate(ZeroPolicy(repeat), normalization, None, "absolute", False,
                                   100 // repeat, (), cases=(STANDARD_CASES[0],), frame_skip=repeat,
                                   physical_case_clock=True, secondary_support=True)
            final = records[0]["final"]
            self.assertEqual(final["milestone_contract"], benchmark_contract(True))
            self.assertTrue(final["milestone_success"][PLATFORM_SUPPORT.name])
            self.assertFalse(final["milestone_success"][FIRST_LEDGE.name])
            self.assertEqual(records[0]["controlled_physics_ticks"], 100)
            self.assertEqual(records[0]["reset_settling_physics_ticks"], 240)
            self.assertTrue(env.closed)

    def test_evaluator_refuses_secondary_metric_on_legacy_contract(self):
        normalization = SimpleNamespace(gamma=RewardConfig().gamma(4), norm_reward=False)
        with patch("research.train.RealGettingOverItEnv") as create:
            with self.assertRaisesRegex(ValueError, "explicit future"):
                evaluate(ZeroPolicy(), normalization, None, "absolute", False, 16, (),
                         secondary_support=True)
            create.assert_not_called()

    def test_one_tick_fidelity_warmup_is_twelve_ticks_and_uses_secondary_metric(self):
        env = MetricFixture(frame_skip=1, horizon=16)
        with patch("research.policy_fidelity.RealGettingOverItEnv", return_value=env):
            rows, _ = rollout(ZeroPolicy(1), RunningMeanStd(shape=(2,)), None,
                              {"frame_skip": 1, "timing_study": True}, 16, STANDARD_CASES[1])
        self.assertEqual([row["applied_action"] for row in rows[:12]], [[-0.5, 0.5]] * 12)
        self.assertEqual(rows[12]["applied_action"], [0.0, 0.0])
        self.assertEqual(rows[-1]["info"]["milestone_contract"], benchmark_contract(True))

    def test_fidelity_refuses_unversioned_one_tick_or_discount_mismatch(self):
        for config, model in (({"frame_skip": 1}, ZeroPolicy(1)),
                              ({"frame_skip": 1, "timing_study": True}, ZeroPolicy(4)),
                              ({"frame_skip": True}, ZeroPolicy(4))):
            with patch("research.policy_fidelity.RealGettingOverItEnv") as create:
                with self.assertRaises(ValueError):
                    rollout(model, RunningMeanStd(shape=(2,)), None, config, 16)
                create.assert_not_called()

    def test_policy_comparator_checks_action_observation_reward_and_outcome(self):
        from copy import deepcopy
        rows = [{"action": [0.0, 0.0], "applied_action": [0.0, 0.0],
                 "observation": [0.0, 1.0], "reward": 0.0, "info": {}, "state": None}]
        self.assertEqual(compare_rollouts(rows, rows)["max_reward_error"], 0.0)
        for key, changed in (("action", [0.1, 0.0]), ("applied_action", [0.1, 0.0]),
                             ("observation", [0.1, 1.0]), ("reward", 0.1),
                             ("info", {"dead": True})):
            other = deepcopy(rows)
            other[0][key] = changed
            with self.subTest(key=key):
                with self.assertRaises(AssertionError):
                    compare_rollouts(rows, other)
        with self.assertRaises(AssertionError):
            compare_rollouts([], [])

    def test_timing_fidelity_budget_guard_runs_before_starting_fixtures(self):
        from research.timing_fidelity import check
        for ticks in (True, 95, 97, 513):
            with self.subTest(ticks=ticks):
                with self.assertRaises(ValueError):
                    check(None, None, ticks)


if __name__ == "__main__":
    unittest.main()
