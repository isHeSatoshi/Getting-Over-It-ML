import copy
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import gymnasium as gym

from research.case_clock import PhysicalCaseClock
from research.evaluation_cases import STANDARD_CASES
from tools.imitation_noise_probe import (
    CONDITIONS, MaskedNoise, PhysicalCapture, child_environment, configure_bounded_http, first_backend_difference,
    first_remote_difference, require_owned_parent, rollout, validate_plan)


class NoiseProbeTests(unittest.TestCase):
    def plan(self):
        base = "imitation-20261004-v1/imitation_campaign/runs/behavior_cloning_only_seed_7/"
        return {"version": "causal-noise-prefix-suffix-probe-v1", "launched": False,
                "reset_seed": 1001, "ordinary_start": True, "warmup": [], "frame_skip": 1,
                "physics_hz": 30, "case_ticks": 1800,
                "conditions": [{"name": k, "noise_active_intervals_ticks": v} for k, v in CONDITIONS.items()],
                "cutoff_tick": 60, "backends": ["reference", "fast"],
                "noise_seed": 8105, "noise_std": .02, "noise_hold_ticks": 4,
                "maximum_case_rollouts": 8, "maximum_controlled_ticks": 14400,
                "maximum_counted_reset_ticks": 1920, "maximum_counted_physics_ticks": 16320,
                "limits": {"training_updates": 0, "new_paid_reservation": 0, "wall_seconds": 600,
                           "owned_browser_processes_only": True, "binary_max_bytes_each": 8 * 2**20},
                "controller": {"arm": "behavior_cloning_only", "training_seed": 7,
                               "deterministic": True, "torch_threads": 1, "device": "cpu",
                               "normalization": "Matching saved frozen RMS, no fitting"},
                "source_dataset_revision": "5df6c20390ca641d8d10a2c62471e7f4142b922e",
                "model": {"path": base + "model.zip", "size": 1000930,
                          "lfs_sha256": "25ec7c319b7a9eb11c2e3b184debe12c256730af0a36d11762e75a82f7acdb87"},
                "normalizer": {"path": base + "normalization.pkl", "size": 7385,
                               "lfs_sha256": "59bdee0d177e6724b10e84f9797c5a823e97f1ef81652ed23fb0e3c37b0e2493"}}

    def test_global_masked_stream_matches_frozen_case_clock(self):
        case = next(c for c in STANDARD_CASES if c.name == "action_noise_5")
        clock = PhysicalCaseClock(case)
        streams = {name: MaskedNoise(name) for name in CONDITIONS}
        actions = np.random.default_rng(19).uniform(-1, 1, (1800, 1, 2)).astype(np.float32)
        for tick, prediction in enumerate(actions):
            full = clock.apply(prediction, tick)
            values = {name: schedule.apply(prediction, tick) for name, schedule in streams.items()}
            self.assertTrue(np.array_equal(values["full_noise_8105"], full))
            self.assertTrue(np.array_equal(values["nominal"], prediction))
            self.assertTrue(np.array_equal(values["early_noise_8105"], full if tick < 60 else prediction))
            self.assertTrue(np.array_equal(values["late_noise_8105"], prediction if tick < 60 else full))

    def test_invalid_action_or_clock_fails_before_stream_advances(self):
        schedule = MaskedNoise("nominal")
        for action, tick in (([[float("nan"), 0]], 0), ([[2, 0]], 0), ([[0, 0]], 1)):
            with self.assertRaises(ValueError):
                schedule.apply(action, tick)
        schedule.apply([[0, 0]], 0)
        with self.assertRaises(ValueError):
            schedule.apply([[0, 0]], 0)

    def test_child_has_no_credentials_or_user_browser_attachment(self):
        result = child_environment({"HF_TOKEN": "hidden", "SERVICE_PASSWORD": "hidden",
                                    "OTHER_API_KEY": "hidden", "AGENT_BROWSER_CDP": "attachment",
                                    "AGENT_BROWSER_SESSION": "saved", "PATH": "compute"})
        self.assertEqual(result, {"PATH": "compute"})

    def test_plan_rejects_expanded_work_or_changed_conditions(self):
        plan = self.plan()
        validate_plan(plan)
        for key, value in (("case_ticks", 1801), ("maximum_controlled_ticks", 14401),
                           ("noise_seed", 8106), ("cutoff_tick", 64)):
            changed = copy.deepcopy(plan);changed[key] = value
            with self.assertRaises(ValueError):
                validate_plan(changed)
        changed = copy.deepcopy(plan);changed["model"]["lfs_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            validate_plan(changed)

    def test_remote_mismatch_reports_first_action_without_interpreting_hold(self):
        local = {"rows": [{"action": [0.1, 0], "applied_action": [0.1, 0]}]}
        remote = {"trace": [{"action": [0.10000001, 0], "applied_action": [0.1, 0]}]}
        result = first_remote_difference(local, remote)
        self.assertEqual(result["kind"], "action")
        self.assertEqual(result["tick"], 1)
        self.assertGreater(result["maximum_error"], 0)

    def test_backend_difference_requires_exact_observations(self):
        a = {"rows": [{"action": [0, 0], "applied_action": [0, 0],
                        "pre_observation": [0], "observation": [0]}]}
        b = copy.deepcopy(a);b["rows"][0]["observation"] = [1e-9]
        result = first_backend_difference(a, b)
        self.assertEqual(result["kind"], "observation")
        self.assertEqual(result["tick"], 1)

    def test_current_hub_client_factory_enforces_request_deadline(self):
        import httpx
        factory = Mock()
        configure_bounded_http(time.time() + 30, SimpleNamespace(set_client_factory=factory))
        with factory.call_args.args[0]() as client:
            request = httpx.Request("GET", "https://huggingface.co")
            client.event_hooks["request"][0](request)
            self.assertEqual(request.extensions["timeout"]["connect"], 5)
            self.assertLessEqual(request.extensions["timeout"]["read"], 30)
        configure_bounded_http(time.time() - 1, SimpleNamespace(set_client_factory=factory))
        with factory.call_args.args[0]() as client:
            with self.assertRaises(ValueError):
                client.event_hooks["request"][0](httpx.Request("GET", "https://huggingface.co"))

    def test_windows_launcher_exception_is_exact_and_not_a_training_guard(self):
        root = Mock(pid=71);root.create_time.return_value = 100.0
        launcher = Mock(pid=72);launcher.exe.return_value = "/owned/venv/python.exe"
        launcher.parent.return_value = root
        process = Mock();process.parent.return_value = launcher
        prepared = {"parent_pid": 71, "parent_creation_time": 100.0,
                    "launcher_executable": "/owned/venv/python.exe"}
        require_owned_parent(prepared, lambda pid: process, "win32")
        with self.assertRaises(ValueError):
            require_owned_parent(prepared, lambda pid: process, "linux")
        launcher.exe.return_value = "/other/python.exe"
        with self.assertRaises(ValueError):
            require_owned_parent(prepared, lambda pid: process, "win32")
        process.parent.return_value = root
        require_owned_parent(prepared, lambda pid: process, "linux")
        root.create_time.return_value = 101.0
        with self.assertRaises(ValueError):
            require_owned_parent(prepared, lambda pid: process, "linux")

    def test_terminal_physical_state_is_captured_before_vecenv_reset(self):
        from stable_baselines3.common.vec_env import DummyVecEnv
        class Fixture(gym.Env):
            observation_space = gym.spaces.Box(-1, 1, (1,), dtype=np.float32)
            action_space = gym.spaces.Box(-1, 1, (2,), dtype=np.float32)
            def reset(self, *, seed=None, options=None):
                self.state = {"tick": 0}
                return np.zeros(1, dtype=np.float32), {}
            def step(self, action):
                self.state = {"tick": 1}
                return np.zeros(1, dtype=np.float32), 0.0, False, True, {}
        capture = PhysicalCapture(Fixture())
        vector = DummyVecEnv([lambda: capture])
        try:
            vector.reset()
            vector.step(np.zeros((1, 2), dtype=np.float32))
            self.assertEqual(capture.unwrapped.state["tick"], 0)
            self.assertEqual(capture.last_physical_state["tick"], 1)
        finally:
            vector.close()

    def test_rollout_flushes_complete_physical_rows_without_real_game_work(self):
        import tempfile
        from stable_baselines3.common.running_mean_std import RunningMeanStd
        class Fixture(gym.Env):
            gamma = 0.9
            observation_space = gym.spaces.Box(-1, 1, (217,), dtype=np.float32)
            action_space = gym.spaces.Box(-1, 1, (2,), dtype=np.float32)
            def reset(self, *, seed=None, options=None):
                self.state = {"tick": 120}
                return np.zeros(217, dtype=np.float32), {}
            def step(self, action):
                self.state = {"tick": 121}
                return np.zeros(217, dtype=np.float32), 0.0, False, True, {"physics_ticks": 1}
        model = Mock()
        model.predict.return_value = (np.zeros((1, 2), dtype=np.float32), None)
        normalizer = SimpleNamespace(clip_obs=10, epsilon=1e-8,
                                    obs_rms=RunningMeanStd(shape=(217,)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            with patch("research.env.RealGettingOverItEnv", return_value=Fixture()), \
                 patch("research.study_metrics.enable_platform_support"):
                result = rollout(model, normalizer, None, "nominal", float("inf"), path)
            row = json.loads(path.read_text())
            self.assertEqual(row["controlled_ticks_total"], 1)
            self.assertEqual(row["reset_ticks_total"], 240)
            self.assertEqual(row["post_state"]["tick"], 121)
            self.assertEqual(result["rows"], [row])


if __name__ == "__main__":
    unittest.main()
