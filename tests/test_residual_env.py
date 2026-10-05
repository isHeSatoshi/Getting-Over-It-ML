from copy import deepcopy
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.running_mean_std import RunningMeanStd
from stable_baselines3.common.vec_env import DummyVecEnv

from research.evaluation_cases import EvaluationCase
from research.residual_env import ResidualGettingOverItEnv, contract
from research.residual_policy import (LOG_STD, ZeroResidualPolicy, checkpoint_contract,
                                      new_normalizer, validate_checkpoint)
from research.reward import RewardConfig
from research.stroke_controller import StrokeController


def fixture():
    observations = np.zeros((600, 217), np.float32)
    observations[:, 0] = np.arange(600, dtype=np.float32)/5500
    observations[:, 1] = 21/16000
    actions = np.column_stack((np.arange(600)/1000, np.full(600, -.5))).astype(np.float32)
    return observations, actions


class MockRawEnv(gym.Env):
    """Mock transitions never count as original game physics."""
    def __init__(self, finish=None):
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(217,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
        self.action_mode, self.frame_skip, self.horizon = "absolute", 1, 1800
        self.terrain, self.reward_config = object(), RewardConfig()
        self.gamma = self.reward_config.gamma(1)
        self.finish, self.pointer, self.resets = finish, np.zeros(2), 0
        self.state, self.last_info = None, None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.resets += 1
        self.steps, self.pointer = 0, np.zeros(2)
        self.raw = fixture()[0][0].copy()
        self.state = {"tick": 120, "player_world_x": 0, "player_world_y": 21}
        return self.raw.copy(), {"physics_ticks": 0}

    def step(self, action):
        self.steps += 1
        self.pointer = np.asarray(action, np.float64)*128
        self.raw[0] = self.steps/5500
        self.raw[13:15] = action
        dead, success, truncated = False, False, self.steps == 1800
        if self.finish == "dead":
            self.raw[1], dead = -200/16000, True
        elif self.finish == "summit":
            self.raw[1], success = 17000/16000, True
        elif self.finish == "truncated":
            truncated = True
        self.state.update(tick=120+self.steps, player_world_x=float(self.raw[0])*5500,
                          player_world_y=float(self.raw[1])*16000)
        self.last_info = {"physics_ticks": 1, "success": success, "dead": dead,
                          "reward_version": "climb-v2", "reward_profile": "settled"}
        return self.raw.copy(), -.125, dead or success, truncated, self.last_info


class ResidualEnvTests(unittest.TestCase):
    def setUp(self):
        self.prior, self.actions = fixture()
        self.raw_env = MockRawEnv()
        self.adapter = ResidualGettingOverItEnv(self.raw_env, self.prior, self.actions)
        self.zero = np.zeros(2, np.float32)

    def test_contract_terminal_layout_readonly_and_raw_reward(self):
        record = contract()
        self.assertEqual(record["environment"]["horizon"], 1800)
        self.assertIn("No base.action", record["next_context"])
        self.assertIn("Same222", record["terminal_context"])
        self.assertFalse(record["reward_normalization"])

    def test_environment_contract_rejects_changed_settings(self):
        for field, value in (("frame_skip", 4), ("horizon", 1801), ("action_mode", "velocity"),
                             ("terrain", None), ("gamma", .99)):
            env = MockRawEnv()
            setattr(env, field, value)
            with self.assertRaises(ValueError):
                ResidualGettingOverItEnv(env, self.prior, self.actions)
        env = MockRawEnv()
        env.observation_space = spaces.Box(-1, 1, shape=(222,), dtype=np.float32)
        with self.assertRaises(ValueError):
            ResidualGettingOverItEnv(env, self.prior, self.actions)

    def test_reset_and_cached_next_observation_never_advance_source(self):
        first, _ = self.adapter.reset(seed=42)
        self.assertEqual(first.shape, (222,))
        self.assertEqual(self.adapter.controller.summary()["base_calls"], 0)
        for _ in range(5):
            self.adapter.current_observation()
        self.assertEqual(self.adapter.controller.summary()["base_calls"], 0)
        next_obs, reward, terminal, truncated, info = self.adapter.step(self.zero)
        self.assertEqual(reward, -.125)
        self.assertFalse(terminal or truncated)
        self.assertEqual(info["residual_transition"]["base_calls"], 1)
        self.assertEqual(self.adapter.controller.summary()["base_calls"], 1)
        self.assertEqual(next_obs[217], np.float32(1/599))

    def test_pure_next_proposal_equals_unchanged_base_for_all1800_phases(self):
        self.adapter.reset()
        base = StrokeController(self.prior, self.actions, "contact_timed_feedback")
        for tick in range(1800):
            pre = self.adapter.current_observation()
            expected = base.action(pre[:217])
            self.assertEqual(pre[218:220].tobytes(), expected.tobytes())
            post, _, terminal, truncated, info = self.adapter.step(self.zero)
            self.assertEqual(info["residual_transition"]["base_calls"], tick+1)
            self.assertEqual(post[217], np.float32(min(tick+1, 599)/599))
        self.assertTrue(truncated)
        self.assertFalse(terminal)
        self.assertEqual(self.adapter.controller.summary()["base_calls"], 1800)
        with self.assertRaises(ValueError):
            self.adapter.step(self.zero)

    def test_nonzero_issued_applied_fields_and_unmodified_reward_info(self):
        self.adapter.reset()
        next_obs, reward, _, _, info = self.adapter.step(np.asarray([.25, .25], np.float32))
        self.assertEqual(reward, -.125)
        record = info.pop("residual_transition")["last_transition"]
        self.assertEqual(info, self.raw_env.last_info)
        np.testing.assert_array_equal(record["final_issued"], [.5, 0])
        np.testing.assert_array_equal(next_obs[220:], [.5, 0])
        self.assertFalse(record["teacher_label"])

    def test_external_clock_applies_after_final_and_own_history_stays_issued(self):
        case = EvaluationCase("mock_warmup", 42, ((-.75, .125),))
        adapter = ResidualGettingOverItEnv(self.raw_env, self.prior, self.actions, case=case)
        adapter.reset(seed=42)
        next_obs, _, _, _, info = adapter.step(np.asarray([.25, .25], np.float32))
        record = info["residual_transition"]["last_transition"]
        np.testing.assert_array_equal(record["actual_applied"], [-.75, .125])
        np.testing.assert_array_equal(next_obs[220:], [.5, 0])
        self.assertTrue(record["external_application_changed"])
        adapter.reset()
        np.testing.assert_array_equal(adapter.current_observation()[220:], [0, 0])
        with self.assertRaises(ValueError):
            adapter.reset(seed=41)

    def test_terminal_and_time_limit_contexts_never_call_base_again(self):
        for finish in ("dead", "summit", "truncated"):
            env = MockRawEnv(finish)
            adapter = ResidualGettingOverItEnv(env, self.prior, self.actions)
            adapter.reset()
            post, _, terminal, truncated, info = adapter.step(self.zero)
            self.assertEqual(post.shape, (222,))
            self.assertEqual(post[:217].tobytes(), env.raw.tobytes())
            self.assertEqual(post[217], np.float32(1/599))
            self.assertEqual(adapter.controller.summary()["base_calls"], 1)
            self.assertTrue(terminal or truncated)
            np.testing.assert_array_equal(post[220:], info["residual_transition"]["last_transition"]["final_issued"])
            with self.assertRaises(ValueError):
                adapter.step(self.zero)

    def test_dummy_vec_auto_reset_keeps222_terminal_and_clears_own_memory(self):
        self.raw_env.finish = "truncated"
        vector = DummyVecEnv([lambda: self.adapter])
        vector.reset()
        post, _, done, infos = vector.step(np.asarray([[.25, .25]], np.float32))
        self.assertTrue(done[0])
        self.assertTrue(infos[0]["TimeLimit.truncated"])
        self.assertEqual(infos[0]["terminal_observation"].shape, (222,))
        np.testing.assert_array_equal(infos[0]["terminal_observation"][220:], [.5, 0])
        np.testing.assert_array_equal(post[0, 220:], [0, 0])
        self.assertEqual(self.adapter.controller.summary()["base_calls"], 0)

    def test_bad_residual_rejected_before_physics_then_valid_action_works(self):
        self.adapter.reset()
        for bad in (np.zeros(2), np.asarray([np.nan, 0], np.float32),
                    np.asarray([1.01, 0], np.float32)):
            with self.assertRaises(ValueError):
                self.adapter.step(bad)
            self.assertEqual(self.raw_env.steps, 0)
        self.adapter.step(self.zero)
        self.assertEqual(self.raw_env.steps, 1)

    def test_invalid_physics_fails_closed_until_reset(self):
        self.adapter.reset()
        original = self.raw_env.step
        def bad_step(action):
            result = original(action)
            self.raw_env.state["tick"] += 1
            return result
        with patch.object(self.raw_env, "step", bad_step):
            with self.assertRaisesRegex(ValueError, "transition"):
                self.adapter.step(self.zero)
        with self.assertRaisesRegex(ValueError, "reset"):
            self.adapter.step(self.zero)
        self.adapter.reset()
        self.adapter.step(self.zero)

    def test_source_context_and_infos_are_copied(self):
        self.adapter.reset()
        self.prior[:] = 99
        self.actions[:] = 99
        observation = self.adapter.current_observation()
        observation[:] = 99
        post, _, _, _, info = self.adapter.step(self.zero)
        info["residual_transition"]["last_transition"]["actual_post"][0] = 99
        post[:] = 99
        self.assertNotEqual(self.adapter.current_observation()[0], 99)
        self.assertNotEqual(self.adapter.controller.summary()["last_transition"]["actual_post"][0], 99)


class ResidualPolicyTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.adapter = ResidualGettingOverItEnv(MockRawEnv(), *fixture())

    def policy(self, seed=12):
        torch.manual_seed(seed)
        return ZeroResidualPolicy(self.adapter.observation_space, self.adapter.action_space,
                                  lambda _: .0003)

    def test_mean_head_exact_zero_logstd_and_no_optimizer_state(self):
        policy = self.policy()
        contexts = np.random.default_rng(1).normal(size=(32, 222)).astype(np.float32)
        action, _ = policy.predict(contexts, deterministic=True)
        np.testing.assert_array_equal(action, np.zeros((32, 2), np.float32))
        np.testing.assert_array_equal(policy.log_std.detach().numpy(), np.full(2, LOG_STD, np.float32))
        self.assertEqual(policy.optimizer.state, {})
        with torch.no_grad():
            distribution = policy.get_distribution(torch.as_tensor(contexts)).distribution
        np.testing.assert_array_equal(distribution.mean.numpy(), np.zeros((32, 2), np.float32))
        np.testing.assert_allclose(distribution.stddev.numpy(), .01, rtol=1e-6)

    def test_only_mean_head_differs_from_same_seed_standard_policy(self):
        policy = self.policy()
        torch.manual_seed(12)
        base = ActorCriticPolicy(self.adapter.observation_space, self.adapter.action_space,
                                 lambda _: .0003, net_arch=[256, 256], log_std_init=LOG_STD)
        for key, value in policy.state_dict().items():
            if not key.startswith("action_net."):
                self.assertTrue(torch.equal(value, base.state_dict()[key]), key)

    def test_wrong_spaces_and_initialization_kwargs_rejected(self):
        space217 = spaces.Box(-np.inf, np.inf, shape=(217,), dtype=np.float32)
        with self.assertRaises(ValueError):
            ZeroResidualPolicy(space217, self.adapter.action_space, lambda _: .0003)
        for kwargs in ({"net_arch": [64, 64]}, {"use_sde": True}, {"log_std_init": 0},
                       {"squash_output": True}):
            with self.assertRaises(ValueError):
                ZeroResidualPolicy(self.adapter.observation_space, self.adapter.action_space,
                                   lambda _: .0003, **kwargs)

    def test_fresh222_normalizer_raw_reward_and_terminal_value_input(self):
        self.adapter.env.finish = "truncated"
        vector = new_normalizer(self.adapter)
        self.assertEqual(vector.obs_rms.mean.shape, (222,))
        self.assertEqual(vector.obs_rms.count, .0001)
        self.assertFalse(vector.norm_reward)
        vector.training = False
        policy = self.policy()
        vector.reset()
        _, reward, done, infos = vector.step(np.zeros((1, 2), np.float32))
        self.assertEqual(reward[0], -.125)
        self.assertTrue(done[0])
        terminal = infos[0]["terminal_observation"]
        self.assertEqual(terminal.shape, (222,))
        with torch.no_grad():
            value = policy.predict_values(policy.obs_to_tensor(terminal)[0])
        self.assertEqual(value.shape, (1, 1))
        self.assertTrue(torch.isfinite(value).all())

    def test_checkpoint_guard_rejects_old_rms_and_changed_source_prior_settings(self):
        vector, policy = new_normalizer(self.adapter), self.policy()
        metadata = checkpoint_contract(self.adapter)
        validate_checkpoint(policy, vector, metadata, self.adapter)
        bad = deepcopy(metadata)
        bad["prior"]["actions"] = "0"*64
        with self.assertRaises(ValueError):
            validate_checkpoint(policy, vector, bad, self.adapter)
        vector.obs_rms = RunningMeanStd(shape=(217,))
        with self.assertRaises(ValueError):
            validate_checkpoint(policy, vector, metadata, self.adapter)
        vector.obs_rms = RunningMeanStd(shape=(222,))
        vector.norm_reward = True
        with self.assertRaises(ValueError):
            validate_checkpoint(policy, vector, metadata, self.adapter)

    def test_trusted_saved_reload_preserves_nonzero_state_not_reinitialized_head(self):
        policy = self.policy()
        with torch.no_grad():
            policy.action_net.bias.fill_(.125)
        contexts = np.zeros((3, 222), np.float32)
        expected = policy.predict(contexts, deterministic=True)[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"owned_policy.pth"
            policy.save(path)
            loaded = ZeroResidualPolicy.load(path, device="cpu")
            np.testing.assert_array_equal(loaded.predict(contexts, deterministic=True)[0], expected)
            self.assertTrue(torch.equal(loaded.action_net.bias, policy.action_net.bias))

    def test_actual_ppo_class_initialization_and_reload_without_learning(self):
        vector = new_normalizer(self.adapter)
        vector.training = False
        model = PPO(ZeroResidualPolicy, vector, seed=12, device="cpu",
                    n_steps=8, batch_size=4, n_epochs=1, gamma=self.adapter.gamma)
        context = vector.reset()
        expected = model.predict(context, deterministic=True)[0]
        np.testing.assert_array_equal(expected, np.zeros((1, 2), np.float32))
        self.assertEqual(model.num_timesteps, 0)
        self.assertEqual(model.policy.optimizer.state, {})
        with torch.no_grad():
            model.policy.action_net.bias.fill_(.125)  # Reload fixture, not an optimizer update.
        expected = model.predict(context, deterministic=True)[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"owned_ppo.zip"
            model.save(path)
            loaded = PPO.load(path, env=vector, device="cpu")
            validate_checkpoint(loaded.policy, vector, checkpoint_contract(self.adapter), self.adapter)
            np.testing.assert_array_equal(loaded.predict(context, deterministic=True)[0], expected)
            self.assertEqual(loaded.num_timesteps, 0)


if __name__ == "__main__":
    unittest.main()
