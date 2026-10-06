import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.evaluation_cases import EvaluationCase
from research.goal_demo import DemoActionMatcher
from research.goal_env import GoalEnv
from research.goal_train import TickBudget, train_seed
from tests.test_goal_system import MockGoalRaw


class ScaffoldMock(MockGoalRaw):
    """Same legal 600-tick opening scaffold used by the bounded mock curriculum test."""

    def step(self, applied):
        observation, reward, terminal, truncated, info = super().step(applied)
        if self.count <= 600:
            last = (self.state["player_world_x"], self.state["player_world_y"])
            self.state["player_world_x"] = min(self.count, 400)*322/400
            self.state["player_world_y"] = 21+min(self.count, 400)*83/400
            self.state["player_vx"] = self.state["player_world_x"]-last[0]+float(applied[0])
            self.state["player_vy"] = self.state["player_world_y"]-last[1]+float(applied[1])
            self.state["hammer_world_x"] = self.state["player_world_x"]+30
            self.state["hammer_world_y"] = self.state["player_world_y"]
            observation = self._raw()
        return observation, reward, terminal, truncated, info


class DemoMatcherTests(unittest.TestCase):
    def matcher(self, threshold=10.0):
        rng = np.random.default_rng(0)
        observations = rng.normal(size=(600, 217)).astype(np.float32)
        actions = rng.uniform(-1, 1, size=(600, 2)).astype(np.float32)
        rms = RunningMeanStd(shape=(217,))
        rms.update(observations)
        return observations, actions, DemoActionMatcher(observations, actions, rms, threshold)

    def test_exact_state_returns_its_own_demo_action_and_far_state_returns_none(self):
        observations, actions, matcher = self.matcher()
        action, distance = matcher.seed_action(observations[17])
        self.assertEqual(distance, 0.0)
        np.testing.assert_array_equal(action, actions[17])
        far = np.full(217, 1e6, np.float32)
        action, distance = matcher.seed_action(far)
        self.assertIsNone(action)
        self.assertGreater(distance, 10.0)

    def test_matcher_rejects_bad_inputs_and_bad_prior(self):
        observations, actions, matcher = self.matcher()
        with self.assertRaises(ValueError):
            matcher.seed_action(np.zeros(217, np.float64))
        with self.assertRaises(ValueError):
            matcher.seed_action(np.full(217, np.nan, np.float32))
        rms = RunningMeanStd(shape=(217,))
        rms.update(observations)
        with self.assertRaises(ValueError):
            DemoActionMatcher(observations[:599], actions[:599], rms, 10.0)
        with self.assertRaises(ValueError):
            DemoActionMatcher(observations, actions*2, rms, 10.0)
        with self.assertRaises(ValueError):
            DemoActionMatcher(observations, actions, rms, 0.0)


class FakeDemo:
    def __init__(self, action):
        self.action = np.asarray(action, np.float32)

    def seed_action(self, raw):
        return self.action.copy(), 0.0


class DemoSeededTrainingTests(unittest.TestCase):
    def test_demo_burst_settings_require_the_matcher(self):
        env = GoalEnv(MockGoalRaw(), budget=TickBudget(maximum=10000))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                train_seed(env, np.zeros((600, 2), np.float32), 21, Path(folder)/"owned",
                           guard=lambda: None, maximum=8, replay_capacity=64, checkpoint_every=0,
                           allow_mock=True, demo_burst_start=.01, demo_burst_ticks=5)

    def test_demo_seeded_bursts_issue_actions_and_count_transitions(self):
        # Exploration-only regression: bursts must issue the matcher's action
        # through the normal legal step path and be counted in the summary.
        env = GoalEnv(ScaffoldMock(), budget=TickBudget(maximum=10000))
        issued_log = []
        original = env.step_recorded

        def recording(issued, applied, **kwargs):
            issued_log.append(np.asarray(issued, np.float32).copy())
            return original(issued, applied, **kwargs)

        env.step_recorded = recording
        with tempfile.TemporaryDirectory() as folder:
            def nominal(rng, reset_seed):
                return EvaluationCase("mock_nominal", reset_seed)
            with patch("research.goal_curriculum.perturbation", side_effect=nominal):
                model, targets, report = train_seed(env, np.zeros((600, 2), np.float32), 21,
                    Path(folder)/"owned", guard=lambda: None, maximum=240, replay_capacity=64,
                    checkpoint_every=0, allow_mock=True, demo=FakeDemo([.5, .25]),
                    demo_burst_start=.05, demo_burst_ticks=10)
        seeded = sum(1 for action in issued_log if np.array_equal(action, np.asarray([.5, .25], np.float32)))
        self.assertGreater(seeded, 0)
        self.assertEqual(seeded, report["demo_seed_learner_transitions"])
        self.assertEqual(report["demo_burst_start"], .05)
        self.assertEqual(report["demo_burst_ticks"], 10)
        self.assertEqual(report["learner_transitions"], 240)


if __name__ == "__main__":
    unittest.main()
