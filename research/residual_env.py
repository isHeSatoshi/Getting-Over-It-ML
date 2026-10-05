"""Gym222 adapter with read-only next context and unchanged physical rewards."""
from copy import deepcopy
import hashlib
import math

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from research.case_clock import PhysicalCaseClock
from research.demonstrations import require
from research.residual_controller import (ACTOR_DIMENSION, HORIZON, RAW_DIMENSION,
                                          ResidualController, _raw, contract as scaffold_contract)
from research.reward import RewardConfig
from research.stroke_controller import (CORRECTION_CAP_PIXELS, HAMMER_CONTACT, HAMMER_TRAVEL,
                                       PLANT_TRAVEL_PIXELS, points)

VERSION = "gym222-causal-residual-adapter-v1"


def contract():
    return {
        "version": VERSION, "scaffold": scaffold_contract(),
        "environment": {"action_mode": "absolute", "frame_skip": 1, "horizon": HORIZON,
                        "raw_dimension": RAW_DIMENSION, "ordinary_spawn": [0, 21]},
        "reward": RewardConfig().describe(1),
        "action_space": "Box2float32[-1,1] legal residual, not final physical pointer",
        "observation_space": "Box222float32, same causal layout as scaffold",
        "next_context": "Pure unchanged timed-contact correction equation at min(actual_steps,599). "
                        "No base.action/prepare/physics call when returning or reading observations. "
                        "Actual prepare occurs once inside step and must byte-match cached context.",
        "terminal_context": "Actual final raw217 + continuing clamped source proposal + last OWN final. "
                            "Same222 layout at death/summit/time-limit; never reset or extra action. "
                            "DummyVecEnv preserves this before real auto-reset for PPO bootstrapping.",
        "case_clock": "Optional external legal PhysicalCaseClock after final issuance, never actor input. "
                      "Disabled for ordinary training; resettable separate issued/applied history.",
        "reward_normalization": False, "learning_updates": 0, "teacher_data_admission": False,
        "limit": "Adapter/initialization correctness only; saved traces and mock endpoints are not gameplay."
    }


class ResidualGettingOverItEnv(gym.Wrapper):
    def __init__(self, env, prior_observations, prior_actions, *, case=None):
        require(isinstance(env.observation_space, spaces.Box)
                and env.observation_space.shape == (RAW_DIMENSION,)
                and env.observation_space.dtype == np.float32
                and isinstance(env.action_space, spaces.Box)
                and env.action_space.shape == (2,) and env.action_space.dtype == np.float32
                and np.all(env.action_space.low == -1) and np.all(env.action_space.high == 1),
                "Residual adapter requires the raw217 legal two-axis environment")
        require(env.action_mode == "absolute" and env.frame_skip == 1 and env.horizon == HORIZON
                and env.terrain is not None and env.reward_config == RewardConfig()
                and env.gamma == RewardConfig().gamma(1),
                "Residual adapter requires unchanged one-tick1800/climb-v2 settings")
        super().__init__(env)
        self.controller = ResidualController(prior_observations, prior_actions)
        self._references = points(np.asarray(prior_observations)).copy()
        self._actions = np.asarray(prior_actions).copy()
        self.prior_hashes = {
            "observations": hashlib.sha256(np.asarray(prior_observations).tobytes()).hexdigest(),
            "actions": hashlib.sha256(self._actions.tobytes()).hexdigest()}
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(ACTOR_DIMENSION,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)
        self.gamma = env.gamma
        self.case, self._clock = case, None
        self._active, self._steps, self._tick = False, 0, None
        self._raw_observation = self._context = None
        self._own = np.zeros(2, np.float32)

    def _next_context(self):
        """Pure preview, also valid for a time-limit continuation value."""
        raw, phase = self._raw_observation, min(self._steps, 599)
        correction = self._references[phase, :2]-points(raw)[:2]
        if raw[HAMMER_CONTACT] == 1 and float(raw[HAMMER_TRAVEL])*64 < PLANT_TRAVEL_PIXELS:
            correction = -correction
        magnitude = float(np.linalg.norm(correction))
        if magnitude > CORRECTION_CAP_PIXELS:
            correction *= CORRECTION_CAP_PIXELS/magnitude
        pointer = self._actions[phase].astype(np.float64)*128+correction
        proposal = (np.clip(pointer, -128, 128)/128).astype(np.float32)
        extra = np.asarray([phase/599, *proposal, *self._own], np.float32)
        return np.concatenate((raw, extra))

    def current_observation(self):
        require(self._context is not None, "Reset before reading residual actor context")
        return self._context.copy()

    def reset(self, *, seed=None, options=None):
        self._active = False
        if self.case is not None:
            require(seed is None or seed == self.case.reset_seed, "Evaluation reset seed changed")
            seed = self.case.reset_seed
        raw, info = self.env.reset(seed=seed, options=options)
        raw = _raw(raw)
        require(self.env.state["player_world_x"] == 0 and self.env.state["player_world_y"] == 21
                and info["physics_ticks"] == 0, "Residual reset must be actual ordinary spawn")
        self.controller.reset(raw)
        self._raw_observation, self._own = raw.copy(), np.zeros(2, np.float32)
        self._steps, self._tick = 0, self.env.state["tick"]
        self._clock = PhysicalCaseClock(self.case) if self.case is not None else None
        self._context, self._active = self._next_context(), True
        return self.current_observation(), deepcopy(info)

    def step(self, residual):
        require(self._active, "Actual reset required before residual stepping")
        prepared = self.controller.prepare(self._raw_observation)
        require(prepared.tobytes() == self._context.tobytes(), "Read-only actor preview differs from base")
        issued = self.controller.action(residual)
        applied = issued.copy() if self._clock is None else self._clock.apply(issued[None, :], self._steps)[0]
        self._active = False  # A partial/invalid physical transition cannot be silently reused.
        raw, reward, terminated, truncated, info = self.env.step(applied)
        raw = _raw(raw)
        require(isinstance(terminated, bool) and isinstance(truncated, bool)
                and math.isfinite(float(reward)) and info["physics_ticks"] == 1
                and self.env.state["tick"] == self._tick+1
                and info["reward_version"] == "climb-v2"
                and info["reward_profile"] == "settled"
                and terminated == bool(info["success"] or info["dead"]),
                "Residual adapter received an invalid actual one-tick transition")
        confirmed = (np.asarray(self.env.pointer, dtype=np.float64)/128).astype(np.float32)
        require(confirmed.tobytes() == applied.tobytes(), "Environment applied command memory changed")
        observed = self.controller.observe(raw, confirmed, terminated=terminated, truncated=truncated)
        require(observed["finished"] == (terminated or truncated), "Actual terminal/horizon flags disagree")
        self._raw_observation, self._own = raw.copy(), issued.copy()
        self._steps, self._tick = observed["steps"], self.env.state["tick"]
        self._context, self._active = self._next_context(), not observed["finished"]
        record = deepcopy(info)
        record["residual_transition"] = observed
        return self.current_observation(), reward, terminated, truncated, record
