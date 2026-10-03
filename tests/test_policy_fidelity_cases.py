import unittest
from unittest.mock import patch

import gymnasium as gym
import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.evaluation_cases import STANDARD_CASES, perturb
from research.policy_fidelity import rollout
from research.reward import RewardConfig


class RolloutFixture(gym.Env):
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(2,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def __init__(self, **kwargs):
        self.gamma = RewardConfig().gamma(4)
        self.state = {}
        self.actions = []
        self.reset_seed = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.reset_seed = seed
        self.actions.clear()
        self.state = {"tick": 0}
        return np.zeros(2, dtype=np.float32), {}

    def step(self, action):
        self.actions.append(np.asarray(action).copy())
        self.state = {"tick": len(self.actions)}
        return np.zeros(2, dtype=np.float32), 0.0, False, False, {}


class ZeroPolicy:
    def predict(self, observation, deterministic=True):
        return np.zeros((1, 2), dtype=np.float32), None


class FidelityCaseTests(unittest.TestCase):
    def run_case(self, case):
        env = RolloutFixture()
        with patch("research.policy_fidelity.RealGettingOverItEnv", return_value=env):
            rows, _ = rollout(ZeroPolicy(), RunningMeanStd(shape=(2,)), None, {}, 6, case)
        return env, rows

    def test_declared_warmup_actions_and_reset_seed_are_preserved(self):
        case = next(case for case in STANDARD_CASES if case.name == "hammer_left")
        env, rows = self.run_case(case)
        self.assertEqual(env.reset_seed, case.reset_seed)
        self.assertEqual([row["applied_action"] for row in rows[:3]], [[-0.5, 0.5]] * 3)
        self.assertEqual([row["action"] for row in rows], [[0.0, 0.0]] * 6)
        self.assertEqual(rows[-1]["applied_action"], [0.0, 0.0])

    def test_noise_stream_matches_standard_evaluator_and_repeats(self):
        case = next(case for case in STANDARD_CASES if case.name == "action_noise_2")
        _, first = self.run_case(case)
        _, second = self.run_case(case)
        self.assertEqual(first, second)
        rng = np.random.default_rng(case.noise_seed)
        expected = [perturb(np.zeros((1, 2), dtype=np.float32), case, rng)[0].tolist()
                    for _ in range(6)]
        self.assertEqual([row["applied_action"] for row in first], expected)

    def test_legacy_fixture_uses_unchanged_actions_and_seed(self):
        env, rows = self.run_case(None)
        self.assertEqual(env.reset_seed, 42)
        self.assertEqual([row["applied_action"] for row in rows], [[0.0, 0.0]] * 6)


if __name__ == "__main__":
    unittest.main()
