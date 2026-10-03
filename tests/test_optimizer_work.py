from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO, SAC

from research.optimizer_work import OptimizerWork


class TinyCounterEnv(gym.Env):
    """Synthetic orchestration fixture, never a Getting Over It experiment."""
    observation_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(1,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.tick = 0
        return np.zeros(2, dtype=np.float32), {}

    def step(self, action):
        self.tick += 1
        observation = np.asarray([self.tick / 8, action[0]], dtype=np.float32)
        return observation, -float((action[0] - 0.25) ** 2), False, self.tick >= 8, {}


class OptimizerWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def ppo(self):
        return PPO("MlpPolicy", TinyCounterEnv(), seed=7, n_steps=8, batch_size=4,
                   n_epochs=2, device="cpu", policy_kwargs={"net_arch": [8, 8]})

    def test_ppo_counts_minibatches_not_epochs_and_preserves_weights(self):
        baseline = self.ppo()
        initial = {key: value.clone() for key, value in baseline.policy.state_dict().items()}
        baseline.learn(32)
        self.assertTrue(any(not torch.equal(initial[key], value)
                            for key, value in baseline.policy.state_dict().items()))
        model = self.ppo()
        with OptimizerWork(model, "ppo") as work:
            model.learn(32)
        result = work.summary()
        self.assertEqual(result["optimizer_step_calls"], {"policy": 16})
        self.assertEqual(result["sb3_internal_update_counter"], 8)
        for key, value in baseline.policy.state_dict().items():
            self.assertTrue(torch.equal(value, model.policy.state_dict()[key]), key)
        self.assertFalse(work.handles)

    def test_sac_counts_actor_critic_and_temperature_separately(self):
        model = SAC("MlpPolicy", TinyCounterEnv(), seed=7, learning_starts=0,
                    batch_size=4, buffer_size=32, device="cpu",
                    policy_kwargs={"net_arch": [8, 8]})
        with OptimizerWork(model, "sac") as work:
            model.learn(8)
        self.assertEqual(work.summary()["optimizer_step_calls"],
                         {"actor": 8, "critic": 8, "entropy_temperature": 8})
        self.assertEqual(work.summary()["total_optimizer_step_calls"], 24)

    def test_fixed_sac_temperature_has_no_optimizer_counter(self):
        model = SAC("MlpPolicy", TinyCounterEnv(), seed=7, learning_starts=0,
                    batch_size=4, buffer_size=32, ent_coef=0.2, device="cpu",
                    policy_kwargs={"net_arch": [8, 8]})
        with OptimizerWork(model, "sac") as work:
            model.learn(4)
        self.assertEqual(work.summary()["optimizer_step_calls"], {"actor": 4, "critic": 4})

    def test_hooks_are_removed_on_failure_and_cannot_be_reused(self):
        model = self.ppo()
        work = OptimizerWork(model, "ppo")
        with self.assertRaisesRegex(RuntimeError, "fixture"):
            with work:
                raise RuntimeError("fixture failure")
        model.policy.optimizer.step()
        self.assertEqual(work.summary()["total_optimizer_step_calls"], 0)
        with self.assertRaisesRegex(RuntimeError, "reused"):
            with work:
                pass

    def test_checkpoint_round_trip_during_instrumentation(self):
        model = self.ppo()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.zip"
            with OptimizerWork(model, "ppo") as work:
                model.learn(8)
                model.save(path)
            loaded = PPO.load(path, device="cpu")
            for key, value in model.policy.state_dict().items():
                self.assertTrue(torch.equal(value, loaded.policy.state_dict()[key]), key)
            self.assertEqual(work.summary()["total_optimizer_step_calls"], 4)
            self.assertFalse(loaded.policy.optimizer._optimizer_step_post_hooks)

    def test_duplicate_optimizer_names_are_rejected(self):
        optimizer = torch.optim.SGD([torch.nn.Parameter(torch.ones(1))], lr=0.1)
        model = SimpleNamespace(actor=SimpleNamespace(optimizer=optimizer),
                                critic=SimpleNamespace(optimizer=optimizer),
                                ent_coef_optimizer=None)
        with self.assertRaisesRegex(ValueError, "alias"):
            OptimizerWork(model, "sac")


if __name__ == "__main__":
    unittest.main()
