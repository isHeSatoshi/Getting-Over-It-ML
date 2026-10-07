"""The challenge Gymnasium environment.

This is a thin, stable wrapper over `research.env.RealGettingOverItEnv`. It
pins the settings a submission must be scored under and adds the challenge's
region tracker. It deliberately does NOT reimplement anything: the physics is
the original game's, executed by the original renderer.
"""
import numpy as np

from challenge.tiers import (TIER_REGIONS, REGION_HOLD_TICKS, SUCCESS_Y, DEATH_Y,
                             START_Y_MIN, START_Y_MAX)
from research.env import BASE_FEATURES, RealGettingOverItEnv


class RegionTracker:
    """Physical hold detector. Evaluation only, never a reward."""

    def __init__(self, regions=TIER_REGIONS, physics_hz=30.0):
        self.regions = tuple(regions)
        self.physics_hz = physics_hz
        self.reset()

    def reset(self):
        self.elapsed = 0
        self.first_reach = {}
        self.successes = {}
        self.best_hold = {r.name: 0 for r in self.regions}
        self._windows = {r.name: [] for r in self.regions}

    def advance(self, trace):
        for state in trace:
            x, y = float(state["player_world_x"]), float(state["player_world_y"])
            vx, vy = float(state["player_vx"]), float(state["player_vy"])
            if not all(np.isfinite(v) for v in (x, y, vx, vy)):
                raise ValueError("Non-finite telemetry in region tracking")
            self.elapsed += 1
            alive = not state["dead"] and not state["success"]
            for region in self.regions:
                inside = (region.x_min <= x <= region.x_max
                          and region.y_min <= y <= region.y_max and alive)
                if inside and region.name not in self.first_reach:
                    self.first_reach[region.name] = self.elapsed / self.physics_hz
                if not (inside and math_hypot(vx, vy) <= region.max_speed_per_tick):
                    self._windows[region.name].clear()
                    continue
                window = self._windows[region.name]
                window.append(bool(state["body_collision"]))
                needed = int(round(region.hold_seconds * self.physics_hz))
                if len(window) > needed:
                    del window[0]
                self.best_hold[region.name] = max(self.best_hold[region.name],
                                                  len(window))
                if (len(window) == needed
                        and sum(window) / needed >= region.min_body_contact_fraction):
                    self.successes.setdefault(region.name, self.elapsed / self.physics_hz)
        return self.summary()

    def summary(self):
        return {
            "region_success": {r.name: r.name in self.successes for r in self.regions},
            "region_first_reach_seconds": dict(self.first_reach),
            "region_success_seconds": dict(self.successes),
            "region_best_hold_seconds": {k: v / self.physics_hz
                                         for k, v in self.best_hold.items()},
        }


def math_hypot(a, b):
    return float(np.hypot(a, b))


class GettingOverItChallengeEnv(RealGettingOverItEnv):
    """Challenge-pinned environment.

    Defaults are the scored configuration: absolute pointer actions, four
    physics ticks per decision, terrain observations on, and the raw
    `climb-v2` reward. Submissions may change only what the challenge
    explicitly allows; see docs/CHALLENGE.md.
    """

    def __init__(self, bridge=None, driver="auto", action_mode="absolute",
                 frame_skip=4, horizon=1800, terrain=True, reward_config=None):
        super().__init__(bridge=bridge, driver=driver, action_mode=action_mode,
                         terrain=terrain, frame_skip=frame_skip,
                         horizon=horizon, reward_config=reward_config)
        self.regions = RegionTracker()

    def reset(self, **kwargs):
        observation, info = super().reset(**kwargs)
        self.regions.reset()
        return observation, {**info, **self.regions.summary()}

    def step(self, action):
        observation, reward, terminated, truncated, info = super().step(action)
        info = {**info, **self.regions.advance(
            [{"player_world_x": self.state["player_world_x"],
              "player_world_y": self.state["player_world_y"],
              "player_vx": self.state["player_vx"],
              "player_vy": self.state["player_vy"],
              "body_collision": self.state["body_collision"],
              "dead": self.state["dead"],
              "success": self.state["success"]}])}
        return observation, reward, terminated, truncated, info

    @property
    def retained_gain(self):
        return float(self.state["player_world_y"]) - float(self.spawn_y)


def describe():
    """Human/machine-readable description of the pinned contract."""
    return {
        "game": "Getting Over It (Scratch edition, project 389464290)",
        "physics": "original compiled project, real renderer, no approximation",
        "observation_dim": 217,
        "action_space": "Box(-1, 1, shape=(2,)) = player-relative pointer offset",
        "action_semantics": "action*128 is a player-relative pointer offset, "
                            "applied for frame_skip consecutive physics ticks",
        "frame_skip": 4,
        "physics_hz": 30.0,
        "success_y": SUCCESS_Y,
        "death_y": DEATH_Y,
        "start_y_range": [START_Y_MIN, START_Y_MAX],
        "observation_features": list(BASE_FEATURES) + ["reward features", "terrain rays"],
    }
