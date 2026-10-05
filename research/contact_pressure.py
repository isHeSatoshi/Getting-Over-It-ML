"""Fallible contact-query acquisition and one reach-bounded pressure contrast."""
import math

import numpy as np

from research.demonstrations import require
from research.hammer_target import HammerTargetPhase, OFFSET, contract as target_contract
from research.stroke_controller import HAMMER_CONTACT, HAMMER_TRAVEL

VERSION = "observed-two-query-contact-phase-v1"
PRESSURE_VERSION = "observed-anchor-one-pressure-step-v1"
QUERY_POSTS = 2
TRAVEL_LIMIT = 3.
MAX_PRESSURE = 16.
MIN_PRESSURE_REACH = 26.001
MAX_REACH = 102.


def contract():
    return {"version": VERSION, "target": target_contract(True),
            "qualification": "Two consecutive actual post rawhammerquery==1 and rawlasttravel*64<3; gap resets",
            "failure_priority": "Terminal/target failure first, then querypair, then free geometric completion fails",
            "maximum_steps": 30, "capture": "Raw actual hammer-world point at acquired post, copied once",
            "query_proxy_not_endpoint_plant_or_bodyauthority": True, "no_rearm_or_cap_renewal": True,
            "teacher_data_admission": False, "training_updates": 0,
            "pressure": {"version": PRESSURE_VERSION, "steps": 1,
                         "anchor": "Same actual raw observed handoff hammer-world anchor in both arms",
                         "direction": "-(fixed source300 body-current raw body)/.2, norm16MAX",
                         "reach_guard": "Analytic FIRST inner26.001/outer102 circle intersection along ONEdirection",
                         "rounding_clearance": .001, "no_search_or_tuned_gain": True,
                         "control": "Float32 anchor/body/offset pointer plus boundeddelta, then unit pastOWNcursor subtraction",
                         "alignment": "Bootstrap actual owncommand/post once; action then one actual observe; no reuse",
                         "bodyauthority_not_predicted_netmotion": True}}


def raw(observation):
    observation = HammerTargetPhase._raw(observation)
    require(observation[HAMMER_CONTACT] in (0, 1) and observation[HAMMER_TRAVEL] >= 0,
            "Contact phase requires binary raw query and nonnegative original travel")
    return observation


def hammer(observation):
    return HammerTargetPhase.body(observation)+observation[6:8].astype(np.float64)*102


class ContactTargetPhase:
    def __init__(self, goal):
        self.target = HammerTargetPhase(goal, cursor_feedback=True)
        self.phase, self.reason, self.streak, self.anchor = "active", None, 0, None

    def bootstrap(self, previous_command, actual_post):
        require(self.phase == "active", "Contact attempt finished")
        self.target.bootstrap(previous_command, raw(actual_post))

    def action(self, observation):
        require(self.phase == "active", "Contact attempt finished")
        try:
            return self.target.action(raw(observation))
        except ValueError:
            if self.target.phase == "failed":
                self.phase, self.reason = "failed", self.target.reason
            raise

    def observe(self, observation):
        require(self.phase == "active", "Contact attempt finished")
        observation = raw(observation)
        status = self.target.observe(observation)
        qualifies = observation[HAMMER_CONTACT] == 1 and float(observation[HAMMER_TRAVEL])*64 < TRAVEL_LIMIT
        self.streak = self.streak+1 if qualifies else 0
        if self.target.phase == "failed":
            self.phase, self.reason = "failed", self.target.reason
        elif self.streak >= QUERY_POSTS:
            self.phase, self.anchor = "acquired", hammer(observation).copy()
        elif status["finished"]:
            self.phase, self.reason = "failed", "free_geometric_completion"
        return self.summary()

    def summary(self):
        return {"version": VERSION, "phase": self.phase, "reason": self.reason, "query_streak": self.streak,
                "anchor": None if self.anchor is None else self.anchor.tolist(),
                "target": self.target.summary(), "passed": self.phase == "acquired", "finished": self.phase != "active"}


def pressure_distance(relative_anchor, direction):
    """First boundary on a ray, not a goal/gain sweep or collision solver."""
    radius = float(np.linalg.norm(relative_anchor))
    require(MIN_PRESSURE_REACH <= radius <= MAX_REACH, "Anchor has no safe pressure reach")
    projection = float(np.dot(relative_anchor, direction))
    discriminant = projection*projection-radius*radius+MIN_PRESSURE_REACH**2
    length = MAX_PRESSURE
    if projection < 0 and discriminant >= 0:
        length = min(length, -projection-math.sqrt(discriminant))
    outer = -projection+math.sqrt(max(0., projection*projection+MAX_REACH**2-radius*radius))
    length = min(length, outer)
    require(math.isfinite(length) and length > 0, "No positive legal pressure along declared direction")
    return length


class AnchorPressureStep:
    def __init__(self, anchor, reference_body, pressure):
        require(isinstance(pressure, bool), "Pressure arm must be explicit")
        anchor, reference_body = np.asarray(anchor, np.float64), np.asarray(reference_body, np.float64)
        require(anchor.shape == reference_body.shape == (2,) and np.isfinite(anchor).all()
                and np.isfinite(reference_body).all(), "Expected finite anchor/reference body")
        self.anchor, self.reference_body, self.pressure = anchor.copy(), reference_body.copy(), pressure
        self.pre, self.cursor_estimate, self.issued_command, self.last = None, None, None, None
        self.phase, self.reason = "ready", None

    def bootstrap(self, previous_command, actual_post):
        require(self.phase == "ready" and self.pre is None, "Pressure history already bootstrapped or finished")
        post = raw(actual_post)
        previous_command = np.asarray(previous_command)
        require(previous_command.shape == (2,) and previous_command.dtype == np.float32
                and np.isfinite(previous_command).all() and np.abs(previous_command).max() <= 1,
                "Pressure requires actually issued float32 own command")
        require(-180 <= float(post[1])*16000 <= 16000, "Pressure bootstrap is terminal")
        require(np.array_equal(hammer(post), self.anchor), "Pressure anchor differs from actual raw handoff tip")
        self.pre = post.copy()
        self.cursor_estimate = post[13:15].astype(np.float64)*128-previous_command.astype(np.float64)*128

    def action(self, observation):
        observation = raw(observation)
        require(self.phase == "ready" and self.pre is not None and np.array_equal(observation, self.pre),
                "Pressure needs exact bootstrapped pre, one step only")
        body = HammerTargetPhase.body(observation)
        relative, delta, length = self.anchor-body, np.zeros(2), 0.
        try:
            require(26 <= np.linalg.norm(relative) <= MAX_REACH, "Illegal anchor reach")
            if self.pressure:
                error = self.reference_body-body
                require(np.linalg.norm(error) > 0, "No body-error pressure direction")
                direction = -error/np.linalg.norm(error)
                length = min(MAX_PRESSURE, float(np.linalg.norm(error))/.2, pressure_distance(relative, direction))
                delta = direction*length
            pointer = relative+delta-OFFSET
            require(np.abs(pointer).max() <= 128 and 26 <= np.linalg.norm(relative+delta) <= MAX_REACH,
                    "Illegal bounded pressure request")
            action = (pointer/128).astype(np.float32)
            pointer = action.astype(np.float64)*128-self.cursor_estimate
            require(np.abs(pointer).max() <= 128, "Illegal pressure cursor compensation")
            action = (pointer/128).astype(np.float32)
        except ValueError as error:
            self.phase, self.reason = "failed", str(error)
            raise
        self.phase, self.issued_command = "pending", action.copy()
        self.last = {"version": PRESSURE_VERSION, "pressure": self.pressure, "anchor": self.anchor.tolist(),
                     "reference_body": self.reference_body.tolist(), "delta": delta.tolist(),
                     "pressure_distance_pixels": length, "requested_reach": float(np.linalg.norm(relative+delta)),
                     "past_own_cursor_estimate": self.cursor_estimate.tolist(), "issued_action": action.tolist()}
        return action.copy()

    def observe(self, observation):
        observation = raw(observation)
        require(self.phase == "pending", "No pending pressure step, or step already finished")
        self.phase = "finished"
        self.cursor_estimate = observation[13:15].astype(np.float64)*128-self.issued_command.astype(np.float64)*128
        return self.summary()

    def summary(self):
        return {"version": PRESSURE_VERSION, "phase": self.phase, "reason": self.reason,
                "past_own_cursor_estimate": None if self.cursor_estimate is None else self.cursor_estimate.tolist(),
                "finished": self.phase in ("finished", "failed")}
