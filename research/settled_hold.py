"""Frozen settle-then-hold diagnostic, separate from unchanged milestones."""
import math

from research.milestones import FIRST_LEDGE

VERSION = "observed-settle-then-central-hold-v1"
SETTLE_CAP_TICKS = 30
HOLD_TICKS = 90


def contract():
    return {"version": VERSION, "settling_cap_ticks": SETTLE_CAP_TICKS,
            "hold_ticks": HOLD_TICKS, "physics_hz": 30,
            "region_and_support": FIRST_LEDGE.__dict__.copy(),
            "settled": "Post-action inside unchanged central region, speed<=2, body query hit, alive",
            "measurement": "Start a separate90tick window on the NEXT tick after settling; "
                           "all region/speed ticks qualify and body-query fraction>=.8",
            "failure": "Settling timeout, terminal state, any hold region/speed loss, insufficient "
                       "final body-query fraction; no restart, rearming or cap renewal",
            "changes_original_milestone": False, "teacher_data_admission": False}


class SettledHoldMonitor:
    def __init__(self):
        self.phase, self.settle_ticks, self.hold_ticks = "settling", 0, 0
        self.body_hits, self.last_tick, self.settled_tick = 0, None, None
        self.hold_start_tick, self.reason = None, None

    def advance(self, state):
        values = [float(state[key]) for key in
                  ("player_world_x", "player_world_y", "player_vx", "player_vy")]
        tick = state["tick"]
        if (not all(math.isfinite(value) for value in values) or type(tick) is not int
                or tick < 0 or state["physics_hz"] != 30
                or (self.last_tick is not None and tick != self.last_tick+1)):
            raise ValueError("Expected finite consecutive original30Hz physical states")
        self.last_tick = tick
        if self.phase in ("succeeded", "failed"):
            return self.summary()
        x, y, vx, vy = values
        qualified = (FIRST_LEDGE.x_min <= x <= FIRST_LEDGE.x_max
                     and FIRST_LEDGE.y_min <= y <= FIRST_LEDGE.y_max
                     and math.hypot(vx, vy) <= FIRST_LEDGE.max_speed_per_tick)
        if state["dead"] or state["success"]:
            self.phase, self.reason = "failed", "terminal_state"
        elif self.phase == "settling":
            self.settle_ticks += 1
            if qualified and bool(state["body_collision"]):
                self.phase, self.settled_tick = "holding", tick
                # The settling sample is never counted as a hold sample.
            elif self.settle_ticks == SETTLE_CAP_TICKS:
                self.phase, self.reason = "failed", "settling_timeout"
        elif not qualified:
            self.phase, self.reason = "failed", "hold_region_or_speed_lost"
        else:
            if self.hold_start_tick is None:
                self.hold_start_tick = tick
            self.hold_ticks += 1
            self.body_hits += bool(state["body_collision"])
            if self.hold_ticks == HOLD_TICKS:
                if self.body_hits / HOLD_TICKS >= FIRST_LEDGE.min_body_contact_fraction:
                    self.phase = "succeeded"
                else:
                    self.phase, self.reason = "failed", "insufficient_body_contact"
        return self.summary()

    def summary(self):
        return {"version": VERSION, "phase": self.phase, "settle_ticks": self.settle_ticks,
                "hold_ticks": self.hold_ticks, "hold_body_hits": self.body_hits,
                "settled_physics_tick": self.settled_tick, "hold_start_physics_tick": self.hold_start_tick,
                "last_physics_tick": self.last_tick, "reason": self.reason,
                "passed": self.phase == "succeeded"}
