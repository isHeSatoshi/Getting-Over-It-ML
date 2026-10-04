"""One causal left-edge recenter attempt around the unchanged contact prior."""
import math

import numpy as np

from research.demonstrations import require
from research.env import BASE_FEATURES
from research.settled_hold import SettledHoldMonitor, contract as hold_contract
from research.stroke_controller import StrokeController, contract as base_contract

VERSION = "causal-left-edge-terminal-wrapper-v1"
TRIGGER_DECISION = 600
MAX_DECISIONS = 751
BODY_HIT = BASE_FEATURES.index("body_collision")


def contract():
    return {"version": VERSION, "base_controller": base_contract("contact_timed_feedback"),
            "monitor": hold_contract(), "input": "Raw217float32 pre/post observations only; private resettable phase/clock",
            "alignment": "Exactly one action followed by one observe of its actually applied one-tick transition; "
                         "next pre-input must equal last observed post-input",
            "trigger": "One checkpoint before decision601, after600observed transitions: "
                       "285<=bodyX<305,Y100..112,body query hit,speed<=2",
            "arming_decision": TRIGGER_DECISION, "maximum_decisions": MAX_DECISIONS,
            "plant_pointer_pixels": [26, -56], "plant_ticks": 30,
            "push_pointer_pixels": [0, -56], "push_ticks": 1,
            "release": "Original base control; first release POST-state starts settling monitor, not push post-state",
            "one_attempt": True, "no_rearm": True, "bypassed_checkpoint_never_rearms": True,
            "case_seed_trace_index_input": False, "privileged_reset": False,
            "teacher_data_admission": False, "learning_updates": 0}


class TerminalController:
    def __init__(self, observations, actions):
        self.base = StrokeController(observations, actions, "contact_timed_feedback")
        self.reset()

    def reset(self):
        self.base.reset()
        self.executed, self.phase, self.attempted = 0, "base", False
        self.plant_steps, self.monitor, self.pending = 0, None, None
        self.previous_post, self.last = None, None

    @staticmethod
    def _raw(observation):
        observation = np.asarray(observation)
        require(observation.dtype == np.float32 and observation.shape == (217,)
                and np.isfinite(observation).all() and observation[BODY_HIT] in (0, 1),
                "Terminal wrapper requires raw217float32 observations and a binary body flag")
        return observation

    def action(self, observation):
        observation = self._raw(observation)
        require(self.pending is None, "Observe the actually applied transition before another action")
        require(self.executed < MAX_DECISIONS, "Terminal wrapper decision budget exhausted")
        require(self.phase not in ("succeeded", "failed"), "Terminal attempt is finished; no rearming")
        require(self.previous_post is None or np.array_equal(observation, self.previous_post),
                "Pre-input does not match the last actually observed post-input")
        if self.executed == TRIGGER_DECISION and self.phase == "base":
            speed = math.hypot(float(observation[2])*64, float(observation[3])*64)
            eligible = (np.float32(285/5500) <= observation[0] < np.float32(305/5500)
                        and np.float32(100/16000) <= observation[1] <= np.float32(112/16000)
                        and observation[BODY_HIT] == 1 and speed <= 2)
            self.phase = "plant" if eligible else "bypass"
            self.attempted = bool(eligible)
        proposed = self.base.action(observation)
        stage, action = self.phase, proposed
        if stage == "plant":
            action = np.asarray([26/128, -56/128], np.float32)
        elif stage == "push":
            action = np.asarray([0., -56/128], np.float32)
        self.pending = stage
        self.last = {"version": VERSION, "stage": stage, "executed_ticks": self.executed,
                     "attempted": self.attempted, "base_proposed_action": proposed.tolist()}
        return action.copy()

    def observe(self, observation):
        observation = self._raw(observation)
        require(self.pending is not None, "No pending action for this post-input")
        stage = self.pending
        self.pending, self.executed = None, self.executed+1
        self.previous_post = observation.copy()
        y = float(observation[1])*16000
        if y < -180 or y > 16000:
            self.phase = "failed"
        elif stage == "plant":
            self.plant_steps += 1
            if self.plant_steps == 30:
                self.phase = "push"
        elif stage == "push":
            self.phase, self.monitor = "release", SettledHoldMonitor()
        elif stage == "release":
            self.monitor.advance({"tick": self.executed, "physics_hz": 30,
                                  "player_world_x": float(observation[0])*5500,
                                  "player_world_y": y, "player_vx": float(observation[2])*64,
                                  "player_vy": float(observation[3])*64,
                                  "body_collision": bool(observation[BODY_HIT]), "dead": False, "success": False})
            if self.monitor.phase in ("succeeded", "failed"):
                self.phase = self.monitor.phase
        return self.summary()

    def summary(self):
        return {"version": VERSION, "phase": self.phase, "executed_ticks": self.executed,
                "attempted": self.attempted, "plant_steps": self.plant_steps,
                "pending_stage": self.pending, "monitor": None if self.monitor is None else self.monitor.summary(),
                "finished": self.phase in ("succeeded", "failed")}
