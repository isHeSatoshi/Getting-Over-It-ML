"""Real-game Gymnasium interface with explicit contracts and no silent fallback."""
import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces

from research.browser_bridge import BrowserBridge
from research.terrain import TerrainMap
from research.reward import ClimbReward, RewardConfig, SUCCESS_Y, DEATH_Y
from research.milestones import MilestoneTracker

BASE_FEATURES = (
    "world_x", "altitude", "body_dx", "body_dy", "body_impulse_x", "body_impulse_y",
    "hammer_offset_x", "hammer_offset_y", "hammer_dx", "hammer_dy",
    "angle_sin", "angle_cos", "angular_delta", "pointer_x", "pointer_y",
    "last_tx", "last_ty", "control_memory_x", "control_memory_y",
    "last_hammer_distance", "last_effort",
    "body_collision", "hammer_collision", "hammer_air", "effort", "episode_high",
)


class RealGettingOverItEnv(gym.Env):
    metadata = {"render_modes": ["human"]}
    POINTER_LIMIT = 128.0

    def __init__(self, bridge=None, driver="auto", action_mode="absolute", terrain=True,
                 frame_skip=4, horizon=3000, reward_config=None):
        super().__init__()
        if action_mode not in ("absolute", "velocity", "polar"):
            raise ValueError("Unknown action mode")
        if not isinstance(frame_skip, int) or not 1 <= frame_skip <= 16 or horizon < 1:
            raise ValueError("Invalid environment configuration")
        self.reward_config = reward_config if reward_config is not None else RewardConfig()
        self.reward = ClimbReward(self.reward_config, frame_skip)
        self.milestones = MilestoneTracker(physics_hz=self.reward_config.physics_hz)
        self.bridge = bridge if bridge is not None else BrowserBridge(driver=driver)
        self._owns_bridge = bridge is None
        self.action_mode = action_mode
        self.terrain = TerrainMap() if terrain else None
        self.frame_skip, self.horizon, self.gamma = frame_skip, horizon, self.reward.gamma
        self.action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
        self.observation_feature_names = BASE_FEATURES + self.reward.feature_names
        self.observation_space = spaces.Box(
            -np.inf, np.inf, shape=(len(self.observation_feature_names) + (128 if terrain else 0),), dtype=np.float32)
        self._active = False
        self.state = None
        self.pointer = np.zeros(2, dtype=np.float64)
        self.angle, self.radius = 0.0, 80.0
        self.decision, self.command_id, self.episode_high = 0, 0, 0.0

    def _obs(self, s):
        px, py, hx, hy = (s[k] for k in ("player_world_x", "player_world_y",
                                         "hammer_world_x", "hammer_world_y"))
        angle = s["hammer_angle_rad"]
        base = [
            px / 5500, py / 16000, s["player_vx"] / 64, s["player_vy"] / 64,
            s["player_impulse_vx"] / 64, s["player_impulse_vy"] / 64,
            (hx - px) / 102, (hy - py) / 102, s["hammer_vx"] / 64, s["hammer_vy"] / 64,
            math.sin(angle), math.cos(angle), s["hammer_angular_velocity"] / math.pi,
            s["pointer_x"] / 128, s["pointer_y"] / 128,
            s["last_tx"] / 50, s["last_ty"] / 50,
            s["control_error_memory_x"] / 128, s["control_error_memory_y"] / 128,
            s["last_hammer_distance"] / 64, s["last_effort"] / 50,
            float(s["body_collision"]), float(s["hammer_collision"]),
            min(s["hammer_air"], 300) / 300, s["effort"] / 50, self.episode_high / 16000,
        ]
        base.extend(self.reward.observation())
        if self.terrain:
            if s.get("execution_mode") == "fast":
                base.extend(self.terrain.fast_observation(s))
            else:
                base.extend(self.terrain.observation(s))
        obs = np.asarray(base, dtype=np.float32)
        if obs.shape != self.observation_space.shape or not np.isfinite(obs).all():
            raise RuntimeError("Invalid observation, refusing to train")
        return obs

    @staticmethod
    def _validate_state(s):
        if s["backend"] != "turbowarp-real-renderer" or s["schema_version"] != 2:
            raise RuntimeError("Unvalidated physics backend")
        keys = ("player_world_x", "player_world_y", "hammer_world_x", "hammer_world_y",
                "player_vx", "player_vy", "hammer_vx", "hammer_vy", "frame_id", "tick",
                "game_time", "physics_hz", "pointer_x", "pointer_y",
                "player_impulse_vx", "player_impulse_vy", "hammer_angle_rad", "hammer_angular_velocity",
                "effort", "hammer_air", "last_tx", "last_ty", "control_error_memory_x",
                "control_error_memory_y", "last_hammer_distance", "last_effort", "offset_y",
                "camera_x", "camera_y", "player_screen_x", "player_screen_y", "collision_queries")
        if not all(math.isfinite(s[k]) for k in keys):
            raise RuntimeError("Non-finite game telemetry")
        for key in ("dead", "success", "body_collision", "hammer_collision"):
            if not isinstance(s[key], bool):
                raise RuntimeError("Invalid outcome/contact telemetry")
        if s["success"] != (s["player_world_y"] > SUCCESS_Y) or s["dead"] != (s["player_world_y"] < DEATH_Y):
            raise RuntimeError("Outcome telemetry disagrees with world height")
        if s["physics_hz"] <= 0:
            raise RuntimeError("Invalid physics rate")

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        game_seed = int(self.np_random.integers(0, 2**32))
        s = self.bridge.reset(game_seed)
        self._validate_state(s)
        if s["physics_hz"] != self.reward_config.physics_hz:
            raise RuntimeError("Reward clock does not match the game clock")
        if s["dead"] or s["success"] or not 15 <= s["player_world_y"] <= 30:
            raise RuntimeError("Game did not settle onto the starting terrain")
        if not s["body_collision"] or s["collision_queries"] == 0:
            raise RuntimeError("Missing starting collision physics")
        self.state = s
        self.spawn_y = s["player_world_y"]
        self.episode_high = self.spawn_y
        self.reward.reset(s)
        self.milestones.reset()
        self.pointer[:] = s["pointer_x"], s["pointer_y"]
        self.angle, self.radius = math.pi / 2, 26.0
        self.decision, self.command_id, self._active = 0, 0, True
        return self._obs(s), self._info(s, [])

    def step(self, action):
        if not self._active:
            raise RuntimeError("Reset is required before stepping")
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (2,) or not np.isfinite(action).all():
            raise ValueError("Action must contain two finite values")
        action = np.clip(action, -1, 1)
        old = self.state
        commands = []
        for _ in range(self.frame_skip):
            if self.action_mode == "absolute":
                self.pointer[:] = action * self.POINTER_LIMIT
            elif self.action_mode == "velocity":
                self.pointer = np.clip(self.pointer + action * 8, -self.POINTER_LIMIT, self.POINTER_LIMIT)
            else:
                self.angle += action[0] * 0.12
                self.radius = float(np.clip(self.radius + action[1] * 4, 26, 102))
                self.pointer[:] = self.radius * math.cos(self.angle), self.radius * math.sin(self.angle) - old["offset_y"]
            self.command_id += 1
            commands.append({"x": float(self.pointer[0]), "y": float(self.pointer[1]), "id": self.command_id})
        trace = self.bridge.step_commands(commands)
        if not trace:
            raise RuntimeError("No physical steps occurred")
        if len(trace) > len(commands) or (len(trace) < len(commands) and not (trace[-1]["dead"] or trace[-1]["success"])):
            raise RuntimeError("Unexpected physical trace length")
        previous = old
        for index, s in enumerate(trace):
            self._validate_state(s)
            if s["tick"] != previous["tick"] + 1 or s["frame_id"] != previous["frame_id"] + 1:
                raise RuntimeError("Scheduler/game-frame desynchronization")
            if s["command_id_applied"] != commands[index]["id"]:
                raise RuntimeError("Command acknowledgement mismatch")
            if s["physics_hz"] != self.reward_config.physics_hz or not math.isclose(
                    s["game_time"] - previous["game_time"], 1 / s["physics_hz"], abs_tol=1e-9):
                raise RuntimeError("Physics clock desynchronization")
            for axis in ("x", "y"):
                if abs(s[f"pointer_{axis}"] - commands[index][axis]) > 1.01:
                    raise RuntimeError("Pointer telemetry disagrees with action")
                for prefix in ("player", "hammer"):
                    difference = s[f"{prefix}_world_{axis}"] - previous[f"{prefix}_world_{axis}"]
                    if not math.isclose(s[f"{prefix}_v{axis}"], difference, abs_tol=1e-7):
                        raise RuntimeError("Velocity telemetry disagrees with physical displacement")
                if not math.isclose(s[f"player_screen_{axis}"] + s[f"camera_{axis}"],
                                    s[f"player_world_{axis}"], abs_tol=1e-7):
                    raise RuntimeError("Camera reference-frame mismatch")
            self.episode_high = max(self.episode_high, s["player_world_y"])
            previous = s
        self.state = trace[-1]
        # The controller's memory must agree with the last actually applied command.
        self.pointer[:] = commands[len(trace) - 1]["x"], commands[len(trace) - 1]["y"]
        self.decision += 1
        terminated = self.state["dead"] or self.state["success"]
        truncated = self.decision >= self.horizon and not terminated
        terms = self.reward.advance(trace)
        self.milestones.advance(trace)
        self._active = not (terminated or truncated)
        info = {**self._info(self.state, trace), **terms}
        return self._obs(self.state), float(terms["reward_total"]), bool(terminated), bool(truncated), info

    def _info(self, s, trace):
        return {
            "player_world_x": s["player_world_x"], "player_world_y": s["player_world_y"],
            "episode_high_y": self.episode_high,
            "max_gain": self.episode_high - self.spawn_y,
            "retained_gain": s["player_world_y"] - self.spawn_y,
            "success": bool(s["success"]), "dead": bool(s["dead"]),
            "physics_ticks": len(trace), "body_hit_frames": sum(x["body_collision"] for x in trace),
            "hammer_hit_frames": sum(x["hammer_collision"] for x in trace),
            "backend": s["backend"],
            **self.milestones.summary(),
        }

    def close(self):
        if self._owns_bridge:
            self.bridge.close()
