"""One observed hammer goal pauses source progression, not physical time."""
import numpy as np

from research.demonstrations import require
from research.hammer_target import HammerTargetPhase, OFFSET, contract as goal_contract
from research.stroke_controller import (HAMMER_CONTACT, HAMMER_TRAVEL, StrokeController,
                                       contract as base_contract, points)

VERSION = "causal-source-clock-one-hammer-goal-v1"
CHECKPOINT = 299
MAX_DECISIONS = 751


def contract():
    return {"version": VERSION, "base": base_contract("contact_timed_feedback"),
            "goal_phase": goal_contract(True), "goal": "Hammer world position of fixed raw prior row300",
            "input": "Raw217float32 actual pre/post, own issued command history and private resettable source phase",
            "checkpoint_after_observed_steps": CHECKPOINT, "maximum_decisions": MAX_DECISIONS,
            "trigger": "Previous raw hammerqueryhit1/travel<3 and hammerworldY<goalY-1, legalgoalreach26..102/axes128",
            "source_progress": "First actual goal action consumes one overridden ordinary phase299 proposal; "
                               "basecalls300/source299 freeze until actual completion, then resume ordered phase300",
            "alignment": "Exactly action then actual one-tick observe; next pre equals last post",
            "one_attempt": True, "missed_checkpoint_permanent_bypass": True, "no_rearm_or_phase_jump": True,
            "failed_goal_terminal": True, "case_seed_trace_oracle": False,
            "teacher_data_admission": False, "learning_updates": 0}


class SourceGoalController:
    def __init__(self, observations, actions):
        self.base = StrokeController(observations, actions, "contact_timed_feedback")
        self.goal = self.base.references[300, 2:].copy()
        self.reset()

    def reset(self):
        self.base.reset()
        self.executed, self.phase, self.attempted = 0, "base", False
        self.target, self.pending, self.previous_post, self.issued_command, self.last = None, None, None, None, None

    @staticmethod
    def _raw(observation):
        observation = HammerTargetPhase._raw(observation)
        require(observation[HAMMER_CONTACT] in (0, 1) and observation[HAMMER_TRAVEL] >= 0,
                "Source goal requires a binary query flag and nonnegative previous travel")
        return observation

    def action(self, observation):
        observation = self._raw(observation)
        require(self.pending is None, "Observe the actual transition before another source-goal action")
        require(self.phase != "failed" and self.executed < MAX_DECISIONS, "Source-goal attempt or budget finished")
        require(self.previous_post is None or np.array_equal(observation, self.previous_post),
                "Source-goal pre-input differs from last actual post-input")
        proposed = None
        if self.executed == CHECKPOINT and self.phase == "base":
            body, hammer = points(observation).reshape(2, 2)
            pointer = self.goal-body-OFFSET
            eligible = (observation[HAMMER_CONTACT] == 1 and float(observation[HAMMER_TRAVEL])*64 < 3
                        and hammer[1] < self.goal[1]-1 and 26 <= np.linalg.norm(self.goal-body) <= 102
                        and np.abs(pointer).max() <= 128)
            self.phase, self.attempted = ("goal", True) if eligible else ("bypass", False)
            if eligible:
                require(self.issued_command is not None, "Observed preceding own command is missing")
                self.target = HammerTargetPhase(self.goal, cursor_feedback=True)
                self.target.bootstrap(self.issued_command, observation)
                proposed = self.base.action(observation)
        stage = self.phase
        if stage == "goal":
            try:
                action = self.target.action(observation)
            except ValueError:
                self.phase = "failed"
                raise
        else:
            proposed = self.base.action(observation)
            action = proposed
        self.pending, self.issued_command = stage, action.copy()
        self.last = {"version": VERSION, "stage": stage, "executed_ticks": self.executed,
                     "base_proposed_action": None if proposed is None else proposed.tolist(),
                     "base_source_calls": self.base.calls, "base_source_phase": self.base.phase,
                     "attempted": self.attempted}
        return action.copy()

    def observe(self, observation):
        observation = self._raw(observation)
        require(self.pending is not None, "No pending source-goal action to observe")
        stage, self.pending = self.pending, None
        self.executed += 1
        self.previous_post = observation.copy()
        if stage == "goal":
            status = self.target.observe(observation)
            if status["finished"]:
                self.phase = "resumed" if status["passed"] else "failed"
        if float(observation[1])*16000 < -180 or float(observation[1])*16000 > 16000:
            self.phase = "failed"
        return self.summary()

    def summary(self):
        return {"version": VERSION, "phase": self.phase, "executed_ticks": self.executed,
                "attempted": self.attempted, "source_calls": self.base.calls, "source_phase": self.base.phase,
                "pending_stage": self.pending, "target": None if self.target is None else self.target.summary(),
                "finished": self.phase == "failed"}
