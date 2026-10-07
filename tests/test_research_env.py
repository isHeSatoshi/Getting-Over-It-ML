"""Unit contracts use synthetic states; real physics is tested by research.validate."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

from research.env import RealGettingOverItEnv, BASE_FEATURES
from research.reward import RewardConfig
from research.browser_bridge import BrowserBridge


def state(y=21, tick=120, body=True, dead=False, success=False):
    s = {k: 0.0 for k in (
        "player_world_x", "player_vx", "player_vy", "player_impulse_vx", "player_impulse_vy",
        "hammer_world_x", "hammer_vx", "hammer_vy", "hammer_angle_rad", "hammer_angular_velocity",
        "pointer_x", "pointer_y", "last_tx", "last_ty", "control_error_memory_x",
        "control_error_memory_y", "hammer_air", "effort", "offset_y")}
    s.update(last_hammer_distance=0, last_effort=0)
    s.update(player_world_y=y, hammer_world_y=y + 26, backend="turbowarp-real-renderer",
             schema_version=1, tick=tick, frame_id=tick, body_collision=body,
             hammer_collision=False, collision_queries=2, dead=dead, success=success,
             command_id_applied=0)
    s.update(schema_version=2, physics_hz=30, game_time=tick / 30,
             camera_x=0, camera_y=0, player_screen_x=0, player_screen_y=y)
    return s


class Bridge:
    def __init__(self, scripted=None):
        self.scripted = scripted
        self.commands = []

    def reset(self, seed):
        self.last = state()
        return self.last.copy()

    def step_commands(self, commands):
        self.commands.extend(commands)
        states = []
        for c in commands:
            previous = self.last.copy()
            self.last = self.scripted(self.last) if self.scripted else state(tick=self.last["tick"] + 1)
            for prefix in ("player", "hammer"):
                for axis in ("x", "y"):
                    self.last[f"{prefix}_v{axis}"] = (
                        self.last[f"{prefix}_world_{axis}"] - previous[f"{prefix}_world_{axis}"])
            self.last["command_id_applied"] = c["id"]
            self.last["pointer_x"], self.last["pointer_y"] = c["x"], c["y"]
            states.append(self.last.copy())
            if self.last["dead"] or self.last["success"]:
                break
        return states


class Contracts(unittest.TestCase):
    def env(self, **kwargs):
        return RealGettingOverItEnv(bridge=kwargs.pop("bridge", Bridge()), terrain=False, **kwargs)

    def test_reset_observation_and_idle_reward(self):
        env = self.env()
        obs, _ = env.reset(seed=1)
        self.assertEqual(obs.shape, (len(env.observation_feature_names),))
        self.assertTrue(env.observation_space.contains(obs))
        _, reward, terminated, truncated, _ = env.step([0, 0])
        self.assertAlmostEqual(reward, -0.005 * 4 / 30)
        self.assertFalse(terminated or truncated)

    def test_time_limit_and_required_reset(self):
        env = self.env(horizon=1)
        env.reset()
        _, _, term, trunc, _ = env.step([0, 0])
        self.assertFalse(term)
        self.assertTrue(trunc)
        with self.assertRaises(RuntimeError):
            env.step([0, 0])

    def test_velocity_integrates_per_physics_tick(self):
        bridge = Bridge()
        env = self.env(bridge=bridge, action_mode="velocity")
        env.reset()
        env.step([1, -1])
        self.assertEqual([c["x"] for c in bridge.commands], [8, 16, 24, 32])
        self.assertEqual([c["y"] for c in bridge.commands], [-8, -16, -24, -32])

    def test_terminal_stops_frame_repeat_and_zeroes_potential(self):
        def dying(old):
            s = state(y=-181, tick=old["tick"] + 1, dead=True)
            return s
        env = self.env(bridge=Bridge(dying), action_mode="velocity")
        env.reset()
        _, reward, term, trunc, info = env.step([1, 0])
        self.assertTrue(term)
        self.assertFalse(trunc)
        self.assertEqual(info["physics_ticks"], 1)
        self.assertEqual(env.pointer[0], 8)
        self.assertAlmostEqual(reward, -5 - 0.005 / 30)

    def test_invalid_action_and_desynchronized_state_fail(self):
        env = self.env()
        env.reset()
        for action in ([np.nan, 0], [0], [0, 0, 0]):
            with self.assertRaises(ValueError):
                env.step(action)
        broken = self.env(bridge=Bridge(lambda old: state(tick=old["tick"])))
        broken.reset()
        with self.assertRaisesRegex(RuntimeError, "desynchronization"):
            broken.step([0, 0])

    def test_old_backend_and_false_ground_rejected(self):
        class OldBridge(Bridge):
            def reset(self, seed):
                return {**state(), "backend": "stub"}
        with self.assertRaises(RuntimeError):
            self.env(bridge=OldBridge()).reset()
        class FallingBridge(Bridge):
            def reset(self, seed):
                return state(y=-264)
        with self.assertRaises(RuntimeError):
            self.env(bridge=FallingBridge()).reset()

    def test_terrain_is_recomputed_at_next_state(self):
        class Terrain:
            def observation(self, s):
                self.y = s["player_world_y"]
                return []
        def ascending(old):
            return state(y=old["player_world_y"] + 1, tick=old["tick"] + 1)
        env = self.env(bridge=Bridge(ascending))
        env.terrain = Terrain()
        env.reset()
        env.step([0, 0])
        self.assertEqual(env.terrain.y, 25)

    def test_genuine_altitude_progress_has_correct_potential(self):
        def ascending(old):
            return state(y=old["player_world_y"] + 1, tick=old["tick"] + 1)
        env = self.env(bridge=Bridge(ascending))
        env.reset()
        _, reward, _, _, info = env.step([0, 0])
        self.assertAlmostEqual(reward, env.gamma * env.reward.settled_potential - 0.005 * 4 / 30)
        self.assertEqual(info["retained_gain"], 4)

    def test_discounted_height_cycle_cannot_farm_reward(self):
        positions = iter((121, 21))
        env = self.env(bridge=Bridge(lambda old: state(y=next(positions), tick=old["tick"] + 1)),
                       frame_skip=1)
        env.reset()
        _, first, _, _, _ = env.step([0, 0])
        _, second, _, _, _ = env.step([0, 0])
        self.assertAlmostEqual(first + env.gamma * second, -0.005 / 30 * (1 + env.gamma))

    def test_success_reward_stops_remaining_ticks(self):
        env = self.env(bridge=Bridge(lambda old: state(y=16001, tick=old["tick"] + 1, success=True)))
        env.reset()
        _, reward, term, trunc, info = env.step([0, 0])
        self.assertTrue(term)
        self.assertFalse(trunc)
        self.assertEqual(info["physics_ticks"], 1)
        self.assertAlmostEqual(reward, 100 - 0.005 / 30)

    def test_bad_clock_pointer_velocity_and_camera_fail(self):
        corruptions = {
            "clock": lambda s: s.update(game_time=s["game_time"] + 1),
            "pointer": lambda s: s.update(pointer_x=999),
            "velocity": lambda s: s.update(player_vy=999),
            "camera": lambda s: s.update(player_screen_y=999),
        }
        for name, corrupt in corruptions.items():
            class CorruptBridge(Bridge):
                def step_commands(self, commands):
                    trace = super().step_commands(commands)
                    corrupt(trace[0])
                    return trace
            with self.subTest(name=name):
                env = self.env(bridge=CorruptBridge())
                env.reset()
                with self.assertRaises(RuntimeError):
                    env.step([0, 0])

    def test_reward_clock_mismatch_rejected(self):
        env = self.env(reward_config=RewardConfig(physics_hz=60))
        with self.assertRaisesRegex(RuntimeError, "clock"):
            env.reset()

    def test_reward_history_observed_and_profiles_share_spaces(self):
        spaces = []
        for profile in ("sparse", "height", "settled"):
            env = self.env(reward_config=RewardConfig(profile=profile))
            obs, _ = env.reset()
            self.assertEqual(len(env.reward.observation()), 63)
            self.assertEqual(obs.shape, (len(BASE_FEATURES) + 63,))
            spaces.append(obs.shape)
        self.assertEqual(spaces[0], spaces[1])
        self.assertEqual(spaces[1], spaces[2])

    def test_browser_failure_preserves_json_diagnostic(self):
        bridge = object.__new__(BrowserBridge)
        bridge._cli = ["unused"]
        reply = SimpleNamespace(returncode=1, stdout='{"success":false,"error":"evaluation failed"}', stderr="")
        with patch("research.browser_bridge.subprocess.run", return_value=reply):
            with self.assertRaisesRegex(RuntimeError, "evaluation failed"):
                bridge._command(["eval"])


if __name__ == "__main__":
    unittest.main()
