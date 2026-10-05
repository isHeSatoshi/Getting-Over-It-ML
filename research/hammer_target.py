"""Bounded raw-observation hammer-world completion, not body acquisition."""
import math

import numpy as np

from research.demonstrations import require

VERSION = "observed-fixed-hammer-world-target-v1"
MAX_STEPS = 30
TOLERANCE = 1.
OFFSET = np.asarray([0., 20.])


def contract():
    return {"version": VERSION, "input": "Raw217float32 actual pre/post observations plus one fixed world goal",
            "action": "float32((goal-current raw bodyworld-fixed original render offset0,20)/128)",
            "completion": "Actual post-action raw hammer-world error<=1pixel, existing stationary tolerance",
            "maximum_steps": MAX_STEPS, "tolerance_pixels": TOLERANCE,
            "legal_pointer_axes": 128, "legal_target_reach": [26, 102],
            "alignment": "One action then one actual one-tick post observe; next pre equals last post",
            "query_release_is_completion": False, "body_alignment_is_demonstrated": False,
            "no_rearm_or_cap_renewal": True, "teacher_data_admission": False, "learning_updates": 0}


class HammerTargetPhase:
    def __init__(self, goal):
        goal = np.asarray(goal, dtype=np.float64)
        require(goal.shape == (2,) and np.isfinite(goal).all(), "Expected one finite hammer-world goal")
        self.goal = goal.copy()
        self.steps, self.phase, self.reason = 0, "active", None
        self.pending, self.previous_post, self.last_error = False, None, None

    @staticmethod
    def _raw(observation):
        observation = np.asarray(observation)
        require(observation.shape == (217,) and observation.dtype == np.float32
                and np.isfinite(observation).all(), "Hammer target requires raw217float32 inputs")
        return observation

    @staticmethod
    def body(observation):
        return observation[:2].astype(np.float64)*[5500, 16000]

    def action(self, observation):
        observation = self._raw(observation)
        require(self.phase == "active" and self.steps < MAX_STEPS, "Hammer target attempt finished")
        require(not self.pending, "Observe the actual transition before another action")
        require(self.previous_post is None or np.array_equal(observation, self.previous_post),
                "Pre-input differs from last actual post-input")
        body = self.body(observation)
        pointer = self.goal-body-OFFSET
        reach = float(np.linalg.norm(self.goal-body))
        if np.abs(pointer).max() > 128 or not 26 <= reach <= 102:
            self.phase, self.reason = "failed", "illegal_target"
            raise ValueError("Hammer-world target exceeds legal pointer or reach bounds")
        self.pending = True
        return (pointer/128).astype(np.float32)

    def observe(self, observation):
        observation = self._raw(observation)
        require(self.pending and self.phase == "active", "No pending target action for this post-input")
        self.pending, self.steps = False, self.steps+1
        self.previous_post = observation.copy()
        body = self.body(observation)
        hammer = body+observation[6:8].astype(np.float64)*102
        self.last_error = math.dist(self.goal, hammer)
        if body[1] < -180 or body[1] > 16000:
            self.phase, self.reason = "failed", "terminal_altitude"
        elif self.last_error <= TOLERANCE:
            self.phase = "succeeded"
        elif self.steps == MAX_STEPS:
            self.phase, self.reason = "failed", "target_timeout"
        return self.summary()

    def summary(self):
        return {"version": VERSION, "phase": self.phase, "steps": self.steps,
                "last_raw_hammer_target_error": self.last_error, "reason": self.reason,
                "pending": self.pending, "passed": self.phase == "succeeded",
                "finished": self.phase != "active"}
