"""Causal fixed-transform goal observations, unchanged original game, separate reward."""
from collections import deque
from copy import deepcopy
import math

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from research.demonstrations import require
from research.env import BASE_FEATURES
from research.goal_study import SUFFIX_TICKS
from research.reward import RewardConfig

FRAME = 155
DIMENSION = 620
GOAL_SLICE = slice(151, 153)
SELECTED = list(range(21))+[BASE_FEATURES.index("hammer_air"), BASE_FEATURES.index("effort")]


def schema():
    return {"version": "causal-goal-stack620-v1", "raw_shape": 217, "frames": 4, "frame_shape": FRAME,
            "dimension": DIMENSION, "ordering": "oldest-to-newest",
            "frame": [*BASE_FEATURES[:21], "hammer_air", "effort", "terrain128",
                      "goal_dx/150", "goal_dy/150", "previous_own_issued_x", "previous_own_issued_y"],
            "affine": "Existing env scales, identity afterward; goal XY deltas/150; no clipping/RMS",
            "excluded": ["reward_history", "query_flags", "source_phase", "seeds", "future_noise"],
            "reset_padding": "Repeat actual first frame four times; legal prefixes populate actual history"}


def xy(value):
    result = np.asarray(value, np.float64)
    require(result.shape == (2,) and np.isfinite(result).all(), "Expected finite physical XY")
    return result


def action(value):
    result = np.asarray(value)
    require(result.shape == (2,) and result.dtype == np.float32 and np.isfinite(result).all()
            and np.abs(result).max() <= 1, "Expected own legal float32 pointer command")
    return result


def local_reward(body, goal, speed, dead):
    require(type(dead) is bool and math.isfinite(float(speed)) and speed >= 0, "Invalid goal reward telemetry")
    distance = float(np.linalg.norm(xy(goal)-xy(body)))
    return -min(distance/100, 2)-.05*min(float(speed)/2, 10)+float(distance <= 12 and speed <= 2)-10*dead


def relabel(observation, bodies, goal):
    result = np.asarray(observation, np.float32).reshape(4, FRAME).copy()
    bodies = np.asarray(bodies, np.float64)
    require(bodies.shape == (4, 2) and np.isfinite(result).all() and np.isfinite(bodies).all(),
            "Invalid causal stacked body history")
    result[:, GOAL_SLICE] = ((xy(goal)-bodies)/150).astype(np.float32)
    return result.reshape(DIMENSION)


class GoalHistory:
    def __init__(self):
        self.frames, self.bodies = deque(maxlen=4), deque(maxlen=4)

    def push(self, raw, body, previous_own):
        raw, body, previous_own = np.asarray(raw), xy(body), action(previous_own)
        require(raw.shape == (217,) and raw.dtype == np.float32 and np.isfinite(raw).all(),
                "Goal history requires actual raw217float32")
        frame = np.concatenate((raw[SELECTED], raw[-128:], np.zeros(2, np.float32), previous_own))
        require(frame.shape == (FRAME,), "Changed goal frame layout")
        self.frames.append(frame.copy())
        self.bodies.append(body.copy())
        if len(self.frames) == 1:
            for _ in range(3):
                self.frames.append(frame.copy())
                self.bodies.append(body.copy())

    def reset(self, raw, body):
        self.frames.clear()
        self.bodies.clear()
        self.push(raw, body, np.zeros(2, np.float32))

    def observation(self, goal):
        require(len(self.frames) == 4, "Goal history not initialized")
        return relabel(np.asarray(self.frames).reshape(DIMENSION), np.asarray(self.bodies), goal)

    def body_history(self):
        return np.asarray(self.bodies, np.float64).copy()


class ResetRecorder:
    """Record the actual game seed passed by unchanged RealGettingOverItEnv."""
    def __init__(self, bridge):
        self.bridge, self.last_seed = bridge, None

    def reset(self, seed):
        self.last_seed = int(seed)
        return self.bridge.reset(seed)

    def __getattr__(self, name):
        return getattr(self.bridge, name)


class GoalEnv(gym.Wrapper):
    def __init__(self, env, *, budget=None):
        require(env.action_mode == "absolute" and env.frame_skip == 1
                and env.observation_space.shape == (217,) and env.terrain is not None
                and (getattr(env, "pipeline_mock_only", False) or env.reward_config == RewardConfig()),
                "Goal wrapper requires unchanged one-tick terrain/raw217 controls")
        super().__init__(env)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(DIMENSION,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
        if not isinstance(env.bridge, ResetRecorder):
            env.bridge = ResetRecorder(env.bridge)
        self.history, self.budget = GoalHistory(), budget
        self.goal = np.asarray([0., 21.])
        self.raw = None
        self.suffix_steps, self.active = None, False

    @property
    def body(self):
        return np.asarray([self.env.state["player_world_x"], self.env.state["player_world_y"]], np.float64)

    def set_goal(self, goal):
        self.goal = xy(goal).copy()
        return self.history.observation(self.goal)

    def begin_suffix(self, goal):
        require(self.active, "Suffix needs a legally reached active start")
        self.suffix_steps = 0
        return self.set_goal(goal)

    def reset(self, *, seed=None, options=None):
        if self.budget:
            self.budget.before(120)
        self.active = False
        self.raw, info = self.env.reset(seed=seed, options=options)
        ticks = self.env.state["tick"]
        require(ticks == 120 and self.env.state["player_world_x"] == 0 and self.env.state["player_world_y"] == 21,
                "Goal reset is not ordinary settled spawn")
        if self.budget:
            self.budget.add("resets", ticks)
        self.reset_seed, self.game_seed = seed, self.env.bridge.last_seed
        self.history.reset(self.raw, self.body)
        self.suffix_steps, self.active = None, True
        return self.history.observation(self.goal), deepcopy(info)

    def step_recorded(self, issued, applied, *, category="prefix", eligible=False):
        require(self.active, "Actual reset required after terminal/suffix limit")
        issued, applied = action(issued), action(applied)
        if self.budget:
            self.budget.before(1)
        before = self.history.observation(self.goal)
        bodies = self.history.body_history()
        pre_raw = self.raw.copy()
        old_tick = self.env.state["tick"]
        self.active = False
        raw, original_reward, terminal, truncated, info = self.env.step(applied)
        require(info["physics_ticks"] == 1 and self.env.state["tick"] == old_tick+1,
                "Goal actual game clock mismatch")
        if self.budget:
            self.budget.add(category, 1)
        self.raw = raw.copy()
        self.history.push(raw, self.body, issued)
        if self.suffix_steps is not None:
            self.suffix_steps += 1
            truncated = bool(truncated or (self.suffix_steps >= SUFFIX_TICKS and not terminal))
        speed = math.hypot(self.env.state["player_vx"], self.env.state["player_vy"])
        reward = local_reward(self.body, self.goal, speed, bool(info["dead"]))
        self.active = not (terminal or truncated)
        next_obs = self.history.observation(self.goal)
        transition = {"observation": before, "next_observation": next_obs.copy(),
                      "bodies": bodies, "next_bodies": self.history.body_history(),
                      "action": issued.copy(), "applied": applied.copy(), "goal": self.goal.copy(),
                      "achieved": self.body.copy(), "speed": speed, "dead": bool(info["dead"]),
                      "terminal": terminal, "truncated": truncated, "eligible": bool(eligible),
                      "raw_pre": pre_raw, "raw_post": raw.copy(), "original_reward": float(original_reward)}
        return next_obs, reward, terminal, truncated, {**deepcopy(info), "goal_transition": transition}

    def step(self, issued):
        return self.step_recorded(issued, issued, category="learner", eligible=True)
