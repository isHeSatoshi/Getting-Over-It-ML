"""Physical evaluation metrics, never bonuses or privileged training resets."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Milestone:
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    hold_seconds: float = 3.0
    max_speed_per_tick: float = 2.0
    min_body_contact_fraction: float = 0.8

    def __post_init__(self):
        if not self.name or not all(math.isfinite(v) for k, v in asdict(self).items() if k != "name"):
            raise ValueError("Invalid milestone")
        if self.x_min >= self.x_max or self.y_min >= self.y_max or self.hold_seconds <= 0:
            raise ValueError("Invalid milestone region")
        if self.max_speed_per_tick <= 0 or not 0 <= self.min_body_contact_fraction <= 1:
            raise ValueError("Invalid milestone contact/speed requirement")


FIRST_LEDGE = Milestone("first_ledge_v1", 305.0, 335.0, 100.0, 112.0)
MILESTONES = (FIRST_LEDGE,)


class MilestoneTracker:
    def __init__(self, milestones=MILESTONES, physics_hz=30.0):
        self.milestones, self.physics_hz = tuple(milestones), physics_hz
        if not math.isfinite(physics_hz) or physics_hz <= 0:
            raise ValueError("Invalid milestone clock")
        self.reset()

    def reset(self):
        self.elapsed_ticks = 0
        self.first_reach = {}
        self.successes = {}
        self.windows = {m.name: [] for m in self.milestones}
        self.best_hold = {m.name: 0 for m in self.milestones}

    def advance(self, trace):
        for state in trace:
            x, y, vx, vy = (float(state[k]) for k in (
                "player_world_x", "player_world_y", "player_vx", "player_vy"))
            if not all(math.isfinite(v) for v in (x, y, vx, vy)):
                raise ValueError("Non-finite benchmark telemetry")
            self.elapsed_ticks += 1
            for milestone in self.milestones:
                inside = (milestone.x_min <= x <= milestone.x_max and milestone.y_min <= y <= milestone.y_max
                          and not state["dead"] and not state["success"])
                qualified = inside and math.hypot(vx, vy) <= milestone.max_speed_per_tick
                if inside and milestone.name not in self.first_reach:
                    self.first_reach[milestone.name] = self.elapsed_ticks / self.physics_hz
                window = self.windows[milestone.name]
                if not qualified:
                    window.clear()
                    continue
                window.append(bool(state["body_collision"]))
                needed = math.ceil(milestone.hold_seconds * self.physics_hz)
                if len(window) > needed:
                    del window[0]
                self.best_hold[milestone.name] = max(self.best_hold[milestone.name], len(window))
                if len(window) == needed and sum(window) / needed >= milestone.min_body_contact_fraction:
                    self.successes.setdefault(milestone.name, self.elapsed_ticks / self.physics_hz)
        return self.summary()

    def summary(self):
        return {
            "milestone_contract": [asdict(m) for m in self.milestones],
            "milestone_success": {m.name: m.name in self.successes for m in self.milestones},
            "milestone_first_reach_seconds": {m.name: self.first_reach.get(m.name) for m in self.milestones},
            "milestone_success_seconds": {m.name: self.successes.get(m.name) for m in self.milestones},
            "milestone_best_hold_seconds": {m.name: self.best_hold[m.name] / self.physics_hz for m in self.milestones},
        }
