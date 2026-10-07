"""Versioned task reward and potential shaping, independent of any RL library.

Collision events are used only to qualify a settled-height descriptor. They
never pay a contact bonus. Full rolling history is exposed to the policy.
"""
from collections import deque
from dataclasses import asdict, dataclass
import math

REWARD_VERSION = "climb-v2"
PROFILES = ("sparse", "height", "settled")
SUCCESS_Y = 16000.0
DEATH_Y = -180.0


@dataclass(frozen=True)
class RewardConfig:
    profile: str = "settled"
    physics_hz: float = 30.0
    discount_half_life_seconds: float = 120.0
    success_reward: float = 100.0
    death_penalty: float = 5.0
    time_cost_per_second: float = 0.005
    potential_budget: float = 4.0
    height_scale: float = 100.0
    airborne_weight: float = 0.25
    settled_window_seconds: float = 1.0
    settled_fraction: float = 0.8
    settled_speed_per_tick: float = 2.0

    def __post_init__(self):
        if self.profile not in PROFILES:
            raise ValueError("Unknown reward profile")
        values = asdict(self)
        if not all(math.isfinite(value) for key, value in values.items() if key != "profile"):
            raise ValueError("Reward configuration must be finite")
        for key in ("physics_hz", "discount_half_life_seconds", "success_reward", "death_penalty",
                    "potential_budget", "height_scale", "settled_window_seconds", "settled_speed_per_tick"):
            if values[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if self.time_cost_per_second < 0 or not 0 <= self.airborne_weight <= 1:
            raise ValueError("Invalid cost or airborne weight")
        if not 0 < self.settled_fraction <= 1:
            raise ValueError("Invalid settled fraction")
        raw_window_ticks = round(self.settled_window_seconds * self.physics_hz)
        if not 1 <= raw_window_ticks <= 300:
            raise ValueError("Settled window must contain 1..300 ticks")
        # Bound the cost of indefinite idling under the physical-time discount.
        # Immediate death must not beat idling solely to avoid the clock cost.
        worst_step_seconds = 16 / self.physics_hz
        self.gamma(1)
        idle_cost_bound = self.time_cost_per_second * worst_step_seconds / (1 - self.gamma(16))
        if self.death_penalty <= idle_cost_bound:
            raise ValueError("Death penalty is too small relative to discounted idle cost")
        if self.success_reward <= self.potential_budget + self.death_penalty:
            raise ValueError("Success reward must dominate the shaping budget and failure cost")

    @property
    def window_ticks(self):
        return round(self.settled_window_seconds * self.physics_hz)

    def gamma(self, frame_skip):
        if not isinstance(frame_skip, int) or not 1 <= frame_skip <= 16:
            raise ValueError("Action repeat must contain 1..16 ticks")
        discount = 2 ** (-frame_skip / (self.physics_hz * self.discount_half_life_seconds))
        if not 0 < discount < 1:
            raise ValueError("Discount half-life is outside the usable numeric range")
        return discount

    def describe(self, frame_skip):
        gamma = self.gamma(frame_skip)
        return {
            "version": REWARD_VERSION, **asdict(self),
            "frame_skip": frame_skip, "gamma": gamma, "window_ticks": self.window_ticks,
            "success_y": SUCCESS_Y, "death_y": DEATH_Y,
            "discounted_idle_cost_bound": (
                self.time_cost_per_second * frame_skip / self.physics_hz / (1 - gamma)),
        }


class ClimbReward:
    def __init__(self, config=None, frame_skip=4):
        self.config = config if config is not None else RewardConfig()
        self.frame_skip = frame_skip
        self.gamma = self.config.gamma(frame_skip)
        self._active = False

    def reset(self, state):
        self.spawn_y = float(state["player_world_y"])
        if not math.isfinite(self.spawn_y) or not DEATH_Y < self.spawn_y < SUCCESS_Y:
            raise ValueError("Invalid reward origin")
        self.gains = deque([0.0] * self.config.window_ticks, maxlen=self.config.window_ticks)
        self.stable = deque([0.0] * self.config.window_ticks, maxlen=self.config.window_ticks)
        self.current_gain = self.settled_gain = self.stable_fraction = 0.0
        self._previous_potential = 0.0
        self._active = True

    def _bounded_height(self, gain):
        maximum_gain = SUCCESS_Y - self.spawn_y
        gain = min(maximum_gain, max(0.0, gain))
        # Log compression preserves a nonzero gradient above the first ledge;
        # clipping gain/100 at a small budget would stop shaping after 400 units.
        return (self.config.potential_budget * math.log1p(gain / self.config.height_scale)
                / math.log1p(maximum_gain / self.config.height_scale))

    @property
    def height_potential(self):
        return self._bounded_height(self.current_gain)

    @property
    def settled_potential(self):
        w = self.config.airborne_weight
        return w * self.height_potential + (1 - w) * self._bounded_height(self.settled_gain)

    def _potential(self):
        if self.config.profile == "sparse":
            return 0.0
        if self.config.profile == "height":
            return self.height_potential
        return self.settled_potential

    def advance(self, trace):
        if not self._active:
            raise RuntimeError("Reward must be reset before another transition")
        if not trace or len(trace) > self.frame_skip:
            raise ValueError("Invalid reward transition length")
        # Validate before mutating any reward history.
        for index, s in enumerate(trace):
            py, vx, vy = (float(s[k]) for k in ("player_world_y", "player_vx", "player_vy"))
            if not all(math.isfinite(v) for v in (py, vx, vy)):
                raise ValueError("Non-finite reward state")
            success, dead = py > SUCCESS_Y, py < DEATH_Y
            if s["success"] != success or s["dead"] != dead:
                raise ValueError("Outcome flag does not match world height")
            if (success or dead) and index != len(trace) - 1:
                raise ValueError("Trace advances past a terminal event")
            for key in ("body_collision", "hammer_collision", "dead", "success"):
                if not isinstance(s[key], bool):
                    raise ValueError("Invalid outcome/contact type")
        if len(trace) < self.frame_skip and not (trace[-1]["success"] or trace[-1]["dead"]):
            raise ValueError("Short nonterminal reward transition")
        for s in trace:
            py, vx, vy = (float(s[k]) for k in ("player_world_y", "player_vx", "player_vy"))
            self.current_gain = py - self.spawn_y
            self.gains.append(min(SUCCESS_Y - self.spawn_y, max(0.0, self.current_gain)))
            supported = bool(s["body_collision"] or s["hammer_collision"])
            self.stable.append(float(supported and math.hypot(vx, vy) <= self.config.settled_speed_per_tick
                                     and not (s["success"] or s["dead"])))
        end = trace[-1]
        terminated = bool(end["success"] or end["dead"])
        self.stable_fraction = sum(self.stable) / self.config.window_ticks
        self.settled_gain = min(self.gains) if self.stable_fraction >= self.config.settled_fraction else 0.0
        # Terminal potential is always zero. Time-limit truncation is deliberately
        # not an input here: it bootstraps from the real final observation.
        before = self._previous_potential
        after = 0.0 if terminated else self._potential()
        shaping = self.gamma * after - before
        success_reward = self.config.success_reward if end["success"] else 0.0
        death_cost = -self.config.death_penalty if end["dead"] else 0.0
        elapsed = len(trace) / self.config.physics_hz
        time_cost = -self.config.time_cost_per_second * elapsed
        task = success_reward + death_cost + time_cost
        terms = {
            "reward_version": REWARD_VERSION, "reward_profile": self.config.profile,
            "reward_gamma": self.gamma, "reward_potential_before": before, "reward_potential_after": after,
            "potential_shaping": shaping, "success_reward": success_reward, "death_cost": death_cost,
            "time_cost": time_cost, "task_reward": task, "elapsed_seconds": elapsed,
            "settled_gain": self.settled_gain, "stable_fraction": self.stable_fraction,
            "reward_total": task + shaping,
        }
        self._previous_potential = after
        self._active = not terminated
        return terms

    @property
    def feature_names(self):
        return ("height_potential", "settled_potential", "stable_fraction",
                *(f"height_history_{i}" for i in range(self.config.window_ticks)),
                *(f"stable_history_{i}" for i in range(self.config.window_ticks)))

    def observation(self):
        gain_scale = SUCCESS_Y - self.spawn_y
        return [
            self.height_potential / self.config.potential_budget,
            self.settled_potential / self.config.potential_budget, self.stable_fraction,
            *(gain / gain_scale for gain in self.gains), *self.stable,
        ]
