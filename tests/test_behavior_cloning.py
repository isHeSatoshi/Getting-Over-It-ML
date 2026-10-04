import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from research.behavior_cloning import warm_start
from research.reward import RewardConfig


class Fixture(gym.Env):
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(217,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.steps = 0
        return np.zeros(217, dtype=np.float32), {}

    def step(self, action):
        self.steps += 1
        return np.zeros(217, dtype=np.float32), 0.0, False, self.steps == 8, {}


class CloningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def setup_model(self):
        vector = VecNormalize(DummyVecEnv([Fixture]), norm_reward=False,
                              gamma=RewardConfig().gamma(1))
        model = PPO("MlpPolicy", vector, seed=6, gamma=vector.gamma, n_steps=8,
                    batch_size=4, n_epochs=1, device="cpu",
                    policy_kwargs={"net_arch": [16, 16]})
        self.addCleanup(vector.close)
        return model, vector

    def data(self):
        observations = np.random.default_rng(6).normal(size=(32, 217)).astype(np.float32)
        actions = np.tile([0.5, -0.5], (32, 1)).astype(np.float32)
        return observations, actions

    def test_actor_fits_without_modifying_value_std_ppo_state_or_timesteps(self):
        model, vector = self.setup_model()
        before = {key: value.clone() for key, value in model.policy.state_dict().items()}
        report = warm_start(model, vector, *self.data())
        self.assertLess(report["mean_squared_action_error_after"], report["mean_squared_action_error_before"])
        changed = []
        for key, value in model.policy.state_dict().items():
            if not torch.equal(value, before[key]):
                changed.append(key)
                self.assertTrue(key.startswith(("mlp_extractor.policy_net.", "action_net.")), key)
        self.assertTrue(changed)
        self.assertEqual(model.num_timesteps, 0)
        self.assertFalse(model.policy.optimizer.state)
        self.assertEqual(report["optimizer_step_calls"], 8)
        self.assertFalse(vector.training)
        self.assertEqual(vector.obs_rms.count, 32.0001)

    def test_seeded_warm_start_and_saved_reload_are_identical(self):
        first, a = self.setup_model()
        second, b = self.setup_model()
        warm_start(first, a, *self.data(), seed=6)
        warm_start(second, b, *self.data(), seed=6)
        for key, value in first.policy.state_dict().items():
            self.assertTrue(torch.equal(value, second.policy.state_dict()[key]))
        with tempfile.TemporaryDirectory() as folder:
            first.save(str(Path(folder) / "model"))
            a.save(str(Path(folder) / "normalizer.pkl"))
            restored = PPO.load(str(Path(folder) / "model.zip"), device="cpu")
            restored_vector = VecNormalize.load(str(Path(folder) / "normalizer.pkl"), DummyVecEnv([Fixture]))
            self.addCleanup(restored_vector.close)
            obs = self.data()[0][:1]
            np.testing.assert_array_equal(first.predict(a.normalize_obs(obs), deterministic=True)[0],
                                          restored.predict(restored_vector.normalize_obs(obs), deterministic=True)[0])

    def test_invalid_budgets_discount_data_and_remote_attempts_are_refused(self):
        for kwargs in ({"updates": 9}, {"updates": True}, {"batch_size": 65},
                       {"pipeline_smoke": False}, {"learning_rate": float("nan")}):
            model, vector = self.setup_model()
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                warm_start(model, vector, *self.data(), **kwargs)
        model, vector = self.setup_model()
        vector.gamma = 0.99
        with self.assertRaisesRegex(ValueError, "discounts"):
            warm_start(model, vector, *self.data())
        model, vector = self.setup_model()
        actions = self.data()[1]; actions[0, 0] = 2
        with self.assertRaisesRegex(ValueError, "shapes"):
            warm_start(model, vector, self.data()[0], actions)

    def test_previously_trained_learner_cannot_silently_resume_into_cloning(self):
        model, vector = self.setup_model()
        model.learn(8)
        with self.assertRaisesRegex(ValueError, "fresh learner"):
            warm_start(model, vector, *self.data())

    def test_repeated_smoke_cannot_silently_extend_cloning_budget(self):
        model, vector = self.setup_model()
        warm_start(model, vector, *self.data())
        with self.assertRaisesRegex(ValueError, "fresh learner"):
            warm_start(model, vector, *self.data())

    def test_cli_refuses_full_training_before_data_or_browser_access(self):
        from research.behavior_cloning import main
        with patch("sys.argv", ["cloning", "--dataset", str(Path.cwd() / "missing")]), \
                patch("research.behavior_cloning.load") as load:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main()
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
