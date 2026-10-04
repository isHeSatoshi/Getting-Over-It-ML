import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv

from research.optimizer_work import OptimizerWork
from research.reward import RewardConfig
from research.timing_study import plan
from research.training_timing import PhysicalWork, training_settings


class CounterFixture(gym.Env):
    """Synthetic accounting/weight fixture, never real-game learning evidence."""
    observation_space = gym.spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
    action_space = gym.spaces.Box(-1, 1, shape=(1,), dtype=np.float32)

    def __init__(self, frame_skip=4, short_terminal=False, invalid_ticks=None):
        self.frame_skip, self.short_terminal = frame_skip, short_terminal
        self.invalid_ticks = invalid_ticks
        self.state = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = {"tick": 120}
        self.decision = 0
        return np.zeros(2, dtype=np.float32), {}

    def step(self, action):
        self.decision += 1
        ticks = 1 if self.short_terminal else self.frame_skip
        self.state["tick"] += ticks
        info = {"physics_ticks": ticks if self.invalid_ticks is None else self.invalid_ticks}
        return (np.asarray([self.decision / 8, action[0]], dtype=np.float32),
                -float((action[0] - 0.25) ** 2), self.short_terminal, self.decision >= 8, info)


class TrainingTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_legacy_ppo_and_sac_defaults_are_preserved(self):
        for algorithm in ("ppo", "sac"):
            for smoke in (True, False):
                config = training_settings(algorithm, smoke)
                self.assertEqual(config["frame_skip"], 4)
                self.assertEqual(config["requested_transitions"], 512 if smoke else 1_000_000)
                self.assertEqual(config["episode_decisions"], 256 if smoke else 3000)
                self.assertEqual(config["evaluation_decisions"], 32 if smoke else 450)
                self.assertEqual(config["gamma"], RewardConfig().gamma(4))
                self.assertEqual(config["ppo"], {"n_steps": 64 if smoke else 2048,
                                                "batch_size": 32 if smoke else 256,
                                                "n_epochs": 2 if smoke else 10, "gae_lambda": 0.95})
                self.assertFalse(config["physical_case_clock"])

    def test_full_timing_settings_match_prepared_arm_exactly(self):
        for arm in plan()["arms"]:
            config = training_settings("ppo", False, frame_skip=arm["frame_skip"], timing_study=True)
            self.assertEqual(config["requested_transitions"], arm["transitions"])
            self.assertEqual(config["nominal_controlled_physics_ticks"], arm["max_training_physics_ticks"])
            self.assertEqual(config["episode_decisions"], arm["episode_decisions"])
            self.assertEqual(config["evaluation_decisions"], arm["evaluation_decisions"])
            self.assertEqual(config["gamma"], arm["gamma"])
            self.assertEqual(config["ppo"], {"n_steps": arm["rollout_steps"],
                                            "batch_size": arm["batch_size"],
                                            "n_epochs": arm["epochs"], "gae_lambda": arm["gae_lambda"]})
            calls = (config["requested_transitions"] // config["ppo"]["n_steps"]
                     * config["ppo"]["n_epochs"]
                     * (config["ppo"]["n_steps"] // config["ppo"]["batch_size"]))
            self.assertEqual(calls, 3840)

    def test_timing_smokes_match_physical_time_and_optimizer_calls(self):
        one, four = [training_settings("ppo", True, frame_skip=repeat, timing_study=True)
                     for repeat in (1, 4)]
        for key in ("nominal_controlled_physics_ticks", "episode_physics_ticks", "evaluation_physics_ticks"):
            self.assertEqual(one[key], four[key])
        self.assertEqual(one["ppo"]["n_steps"], four["ppo"]["n_steps"] * 4)
        self.assertEqual(one["ppo"]["batch_size"], four["ppo"]["batch_size"] * 4)
        self.assertAlmostEqual(one["gamma"] ** 4, four["gamma"])
        self.assertAlmostEqual(one["gae_lambda"] ** 4, four["gae_lambda"])

    def test_timing_refuses_undeclared_budgets_and_reward_or_algorithm(self):
        for kwargs in (
            {"frame_skip": 1},
            {"frame_skip": True},
            {"timing_study": True, "steps": 98305},
            {"timing_study": True, "frame_skip": 1, "evaluation_decisions": 450},
            {"timing_study": True, "reward_config": RewardConfig(profile="sparse")},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    training_settings("ppo", False, **kwargs)
        with self.assertRaises(ValueError):
            training_settings("sac", True, timing_study=True)
        with self.assertRaises(ValueError):
            training_settings("ppo", True, timing_study=True, steps=65)
        with self.assertRaises(ValueError):
            training_settings("ppo", True, steps=2049)

    def test_remote_timing_execution_fails_before_creating_artifacts_or_workers(self):
        from research.train import main
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "must_not_exist"
            argv = ["research.train", "--algorithm", "ppo", "--remote-training",
                    "--timing-study", "--frame-skip", "1", "--output-dir", str(output)]
            with patch("sys.argv", argv), patch("research.train.make_bridge") as create:
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    with self.assertRaises(SystemExit):
                        main()
                self.assertIn("bounded runner admission", errors.getvalue())
                create.assert_not_called()
            self.assertFalse(output.exists())

    def test_observed_counts_include_initial_and_auto_reset_separately(self):
        work = PhysicalWork(CounterFixture())
        vector = DummyVecEnv([lambda: work])
        vector.reset()
        for _ in range(16):
            vector.step(np.zeros((1, 1), dtype=np.float32))
        summary = work.summary()
        self.assertEqual(summary["decision_steps"], 16)
        self.assertEqual(summary["controlled_physics_ticks"], 64)
        self.assertEqual(summary["reset_settling_physics_ticks"], 360)
        self.assertEqual(summary["total_counted_physics_ticks"], 424)
        self.assertEqual(summary["resets"], 3)
        vector.close()

    def test_short_terminal_step_is_not_counted_as_full_repeat(self):
        work = PhysicalWork(CounterFixture(short_terminal=True))
        vector = DummyVecEnv([lambda: work])
        vector.reset()
        vector.step(np.zeros((1, 1), dtype=np.float32))
        self.assertEqual(work.summary()["controlled_physics_ticks"], 1)
        self.assertEqual(work.summary()["nominal_controlled_physics_ticks"], 4)
        self.assertEqual(work.summary()["terminal_short_decisions"], 1)
        self.assertEqual(work.summary()["reset_settling_physics_ticks"], 240)
        vector.close()

    def test_invalid_work_telemetry_is_refused(self):
        for ticks in (0, 5, True, 1.5, 2):
            work = PhysicalWork(CounterFixture(invalid_ticks=ticks))
            work.reset()
            with self.subTest(ticks=ticks):
                with self.assertRaisesRegex(RuntimeError, "controlled physics ticks"):
                    work.step(np.zeros(1, dtype=np.float32))
        work = PhysicalWork(CounterFixture())
        with patch.object(work.env, "reset", return_value=(np.zeros(2), {})):
            work.env.state = {"tick": -1}
            with self.assertRaisesRegex(RuntimeError, "reset-settling"):
                work.reset()

    def ppo(self, env):
        return PPO("MlpPolicy", env, seed=7, n_steps=8, batch_size=4,
                   n_epochs=2, device="cpu", policy_kwargs={"net_arch": [8, 8]})

    def test_work_wrapper_preserves_bitwise_ppo_weights_and_optimizer_counts(self):
        baseline = self.ppo(CounterFixture())
        baseline.learn(32)
        work = PhysicalWork(CounterFixture())
        model = self.ppo(work)
        with OptimizerWork(model, "ppo") as optimizer_work:
            model.learn(32)
        for key, value in baseline.policy.state_dict().items():
            self.assertTrue(torch.equal(value, model.policy.state_dict()[key]), key)
        self.assertEqual(optimizer_work.summary()["total_optimizer_step_calls"], 16)
        self.assertEqual(work.summary()["decision_steps"], model.num_timesteps)
        self.assertEqual(work.summary()["controlled_physics_ticks"], 128)

    def test_work_wrapper_preserves_bitwise_sac_weights_and_optimizer_counts(self):
        def sac(env):
            return SAC("MlpPolicy", env, seed=7, learning_starts=0, buffer_size=32,
                       batch_size=4, device="cpu", policy_kwargs={"net_arch": [8, 8]})
        baseline = sac(CounterFixture())
        baseline.learn(16)
        work = PhysicalWork(CounterFixture())
        model = sac(work)
        with OptimizerWork(model, "sac") as optimizer_work:
            model.learn(16)
        for key, value in baseline.policy.state_dict().items():
            self.assertTrue(torch.equal(value, model.policy.state_dict()[key]), key)
        self.assertTrue(torch.equal(baseline.log_ent_coef, model.log_ent_coef))
        self.assertEqual(optimizer_work.summary()["optimizer_step_calls"],
                         {"actor": 16, "critic": 16, "entropy_temperature": 16})
        self.assertEqual(work.summary()["controlled_physics_ticks"], 64)

    def test_physical_work_does_not_change_observations_rewards_or_info(self):
        plain, wrapped = CounterFixture(), PhysicalWork(CounterFixture())
        plain_obs, plain_info = plain.reset(seed=7)
        wrapped_obs, wrapped_info = wrapped.reset(seed=7)
        np.testing.assert_array_equal(plain_obs, wrapped_obs)
        self.assertEqual(plain_info, wrapped_info)
        for _ in range(8):
            a, b = plain.step([0.25]), wrapped.step([0.25])
            np.testing.assert_array_equal(a[0], b[0])
            self.assertEqual(a[1:], b[1:])


if __name__ == "__main__":
    unittest.main()
