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

from research.imitation_train import (
    fine_tune, fit_common_normalizer, learn_arm, require_frozen_rms, rms_snapshot, settings)
from research.imitation_study import plan
from research.reward import RewardConfig
from research.training_timing import PhysicalWork


class Fixture(gym.Env):
    observation_space = gym.spaces.Box(-np.inf, np.inf, shape=(217,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
    frame_skip = 1

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = {"tick": 120}
        self.steps = 0
        return np.zeros(217, dtype=np.float32), {}

    def step(self, action):
        self.state["tick"] += 1
        self.steps += 1
        return (np.full(217, action[0], dtype=np.float32), -float(np.sum(action**2)),
                False, self.steps == 128, {"physics_ticks": 1})


class ImitationTrainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def data(self):
        obs = np.random.default_rng(7).normal(size=(32, 217)).astype(np.float32)
        act = np.tile([0.5, -0.5], (32, 1)).astype(np.float32)
        return obs, act

    def setup_arm(self, arm):
        timing = settings(arm, True)
        physical = PhysicalWork(Fixture())
        vector = VecNormalize(DummyVecEnv([lambda: physical]), norm_reward=False, gamma=timing["gamma"])
        self.addCleanup(vector.close)
        fit_common_normalizer(vector, self.data()[0])
        model = PPO("MlpPolicy", vector, seed=6, device="cpu", gamma=timing["gamma"],
                    **timing["ppo"], policy_kwargs={"net_arch": timing["architecture"]})
        return timing, physical, vector, model

    def test_settings_match_predeclared_full_budget_without_launch(self):
        for arm in plan()["arms"]:
            config = settings(arm, False)
            self.assertEqual(config["gamma"], RewardConfig().gamma(1))
            self.assertEqual(config["architecture"], [256, 256])
            self.assertEqual(config["cloning_updates"], 0 if arm == "ppo_from_scratch" else 2000)
            self.assertEqual(config["rl_transitions"], 0 if arm == "behavior_cloning_only" else 393216)
            self.assertEqual(config["evaluation_decisions"], 1800)
            self.assertEqual(config["ppo"]["n_steps"], 8192)
        with self.assertRaises(ValueError):
            settings("undeclared", True)

    def test_all_arms_share_identical_frozen_normalization_and_initial_weights(self):
        values = [self.setup_arm(arm) for arm in plan()["arms"]]
        for _, _, vector, model in values[1:]:
            for key, value in values[0][3].policy.state_dict().items():
                self.assertTrue(torch.equal(value, model.policy.state_dict()[key]))
            for key, value in rms_snapshot(values[0][2]).items():
                np.testing.assert_array_equal(value, rms_snapshot(vector)[key])
            self.assertFalse(vector.training)

    def test_fitting_twice_or_mutating_frozen_stats_is_refused(self):
        _, _, vector, _ = self.setup_arm("ppo_from_scratch")
        with self.assertRaisesRegex(ValueError, "fresh"):
            fit_common_normalizer(vector, self.data()[0])
        original = rms_snapshot(vector)
        vector.obs_rms.mean[0] += 1
        with self.assertRaisesRegex(ValueError, "changed"):
            require_frozen_rms(vector, original)

    def test_clone_then_ppo_counts_separate_work_and_keeps_rms_frozen(self):
        timing, physical, vector, model = self.setup_arm("behavior_cloning_then_ppo")
        original = rms_snapshot(vector)
        clone, frozen = learn_arm(model, vector, *self.data(), timing, physical, 6)
        self.assertEqual(clone["optimizer_step_calls"], 8)
        self.assertEqual(vector.obs_rms.count, 32.0001)
        self.assertEqual(model.num_timesteps, 0)
        self.assertFalse(model.policy.optimizer.state)
        report = fine_tune(model, vector, timing, physical, frozen)
        self.assertEqual(report["rl_transitions"], 256)
        self.assertEqual(report["physical_work"]["controlled_physics_ticks"], 256)
        self.assertEqual(report["physical_work"]["reset_settling_physics_ticks"], 360)
        self.assertEqual(report["optimizer_work"]["optimizer_step_calls"], {"policy": 4})
        require_frozen_rms(vector, original)

    def test_bc_only_consumes_no_rl_or_training_reset_ticks(self):
        timing, physical, vector, model = self.setup_arm("behavior_cloning_only")
        clone, frozen = learn_arm(model, vector, *self.data(), timing, physical, 6)
        report = fine_tune(model, vector, timing, physical, frozen)
        self.assertEqual(clone["optimizer_step_calls"], 8)
        self.assertEqual(report["rl_transitions"], 0)
        self.assertEqual(report["physical_work"]["total_counted_physics_ticks"], 0)
        self.assertEqual(report["optimizer_work"]["total_optimizer_step_calls"], 0)

    def test_full_settings_and_resumed_learners_are_refused_by_pipeline(self):
        timing, physical, vector, model = self.setup_arm("ppo_from_scratch")
        with self.assertRaisesRegex(ValueError, "remote"):
            learn_arm(model, vector, *self.data(), settings("ppo_from_scratch", False), physical, 6)
        clone, frozen = learn_arm(model, vector, *self.data(), timing, physical, 6)
        self.assertIsNone(clone)
        fine_tune(model, vector, timing, physical, frozen)
        with self.assertRaisesRegex(ValueError, "resume"):
            fine_tune(model, vector, timing, physical, frozen)

    def test_model_budget_drift_fails_before_cloning_or_rollout(self):
        for key, value in (("n_steps", 8192), ("n_epochs", 10), ("gamma", 0.99)):
            timing, physical, vector, model = self.setup_arm("behavior_cloning_then_ppo")
            setattr(model, key, value)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Actual PPO"):
                learn_arm(model, vector, *self.data(), timing, physical, 6)
            self.assertEqual(model.num_timesteps, 0)
            self.assertEqual(physical.decisions, 0)
            self.assertFalse(getattr(model, "_demonstration_warm_started", False))

    def test_physical_repeat_drift_is_refused_before_work(self):
        timing, physical, vector, model = self.setup_arm("behavior_cloning_then_ppo")
        physical.frame_skip = 4
        with self.assertRaisesRegex(ValueError, "physical contract"):
            learn_arm(model, vector, *self.data(), timing, physical, 6)
        self.assertEqual(model.num_timesteps, 0)
        self.assertFalse(getattr(model, "_demonstration_warm_started", False))

    def test_cli_blocks_full_run_before_data_workers_or_output_creation(self):
        from research.imitation_train import main
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "must_not_exist"
            for suffix in ([], ["--remote-training"], ["--smoke", "--remote-training"]):
                argv = ["trainer", "--arm", "behavior_cloning_then_ppo", "--dataset", str(output),
                        "--output-dir", str(output)] + suffix
                with patch("sys.argv", argv), patch("research.imitation_train.load") as load:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        main()
                    load.assert_not_called()
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
