"""Bounded raw-observation hammer-world completion, not body acquisition."""
import math

import numpy as np

from research.demonstrations import require

VERSION = "observed-fixed-hammer-world-target-v1"
FEEDBACK_VERSION = "observed-cursor-feedback-hammer-target-v1"
MAX_STEPS = 30
TOLERANCE = 1.
OFFSET = np.asarray([0., 20.])


def contract(cursor_feedback=False):
    require(isinstance(cursor_feedback, bool), "Cursor feedback must be an explicit boolean")
    record = {"version": VERSION, "input": "Raw217float32 actual pre/post observations plus one fixed world goal",
            "action": "float32((goal-current raw bodyworld-fixed original render offset0,20)/128)",
            "completion": "Actual post-action raw hammer-world error<=1pixel, existing stationary tolerance",
            "maximum_steps": MAX_STEPS, "tolerance_pixels": TOLERANCE,
            "legal_pointer_axes": 128, "legal_target_reach": [26, 102],
            "alignment": "One action then one actual one-tick post observe; next pre equals last post",
            "query_release_is_completion": False, "body_alignment_is_demonstrated": False,
            "no_rearm_or_cap_renewal": True, "teacher_data_admission": False, "learning_updates": 0}
    if cursor_feedback:
        record.update(version=FEEDBACK_VERSION,
                      input="Raw217float32 actual pre/post, fixed goal and actually issued own command history",
                      action="Unit subtract previous actual rawpointer*128 minus previous owncommand*128 "
                             "from uncompensated float32 goal pointer, then float32 action/128",
                      bootstrap="Exactly once before first target action: previous actual own command and its post; "
                                "next pre must equal that post. Caller must verify the preceding transition.",
                      estimate_update="After actual post: rawpointer13/14*128 minus OWN actually issued command*128; "
                                      "never uncompensated desired pointer, current/future noise or seed",
                      filters_or_gain_scan=False)
    return record


class HammerTargetPhase:
    def __init__(self, goal, cursor_feedback=False):
        require(isinstance(cursor_feedback, bool), "Cursor feedback must be an explicit boolean")
        goal = np.asarray(goal, dtype=np.float64)
        require(goal.shape == (2,) and np.isfinite(goal).all(), "Expected one finite hammer-world goal")
        self.goal = goal.copy()
        self.steps, self.phase, self.reason = 0, "active", None
        self.pending, self.previous_post, self.last_error = False, None, None
        self.cursor_feedback, self.cursor_estimate, self.issued_command = cursor_feedback, None, None

    def bootstrap(self, previous_command, actual_post):
        require(self.cursor_feedback and self.phase == "active" and self.steps == 0
                and not self.pending and self.previous_post is None, "Cursor history cannot be bootstrapped here")
        previous_command = np.asarray(previous_command)
        require(previous_command.shape == (2,) and previous_command.dtype == np.float32
                and np.isfinite(previous_command).all() and np.abs(previous_command).max() <= 1,
                "Bootstrap requires one legal float32 previously issued own command")
        actual_post = self._raw(actual_post)
        require(-180 <= float(actual_post[1])*16000 <= 16000, "Bootstrap post is terminal")
        self.previous_post = actual_post.copy()
        self.issued_command = previous_command.copy()
        self.cursor_estimate = actual_post[13:15].astype(np.float64)*128-previous_command.astype(np.float64)*128

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
        require(not self.cursor_feedback or self.cursor_estimate is not None,
                "Bootstrap actual preceding command/post history before feedback action")
        require(self.previous_post is None or np.array_equal(observation, self.previous_post),
                "Pre-input differs from last actual post-input")
        body = self.body(observation)
        pointer = self.goal-body-OFFSET
        reach = float(np.linalg.norm(self.goal-body))
        if np.abs(pointer).max() > 128 or not 26 <= reach <= 102:
            self.phase, self.reason = "failed", "illegal_target"
            raise ValueError("Hammer-world target exceeds legal pointer or reach bounds")
        action = (pointer/128).astype(np.float32)
        if self.cursor_feedback:
            pointer = action.astype(np.float64)*128-self.cursor_estimate
            if np.abs(pointer).max() > 128:
                self.phase, self.reason = "failed", "illegal_cursor_compensation"
                raise ValueError("Past cursor compensation exceeds legal pointer axes")
            action = (pointer/128).astype(np.float32)
        self.issued_command = action.copy()
        self.pending = True
        return action.copy()

    def observe(self, observation):
        observation = self._raw(observation)
        require(self.pending and self.phase == "active", "No pending target action for this post-input")
        self.pending, self.steps = False, self.steps+1
        self.previous_post = observation.copy()
        if self.cursor_feedback:
            self.cursor_estimate = (observation[13:15].astype(np.float64)*128
                                    - self.issued_command.astype(np.float64)*128)
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
        record = {"version": VERSION, "phase": self.phase, "steps": self.steps,
                "last_raw_hammer_target_error": self.last_error, "reason": self.reason,
                "pending": self.pending, "passed": self.phase == "succeeded",
                "finished": self.phase != "active"}
        if self.cursor_feedback:
            record.update(version=FEEDBACK_VERSION,
                          past_cursor_estimate_pixels=None if self.cursor_estimate is None else self.cursor_estimate.tolist(),
                          last_own_command=None if self.issued_command is None else self.issued_command.tolist())
        return record
