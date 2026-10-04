"""Future-study legal evaluation perturbations indexed by physical ticks."""
import math

import numpy as np


class PhysicalCaseClock:
    def __init__(self, case, hold_ticks=4):
        if (not isinstance(hold_ticks, int) or isinstance(hold_ticks, bool)
                or not 1 <= hold_ticks <= 16):
            raise ValueError("Invalid perturbation hold duration")
        if not math.isfinite(case.action_noise_std) or case.action_noise_std < 0:
            raise ValueError("Invalid action noise scale")
        warmup = np.asarray(case.warmup, dtype=np.float32)
        if warmup.size and (warmup.ndim != 2 or warmup.shape[1] != 2
                            or not np.isfinite(warmup).all() or np.abs(warmup).max() > 1):
            raise ValueError("Invalid legal warm-up targets")
        self.case, self.hold_ticks = case, hold_ticks
        self.warmup = warmup.reshape(-1, 2)
        self.rng = np.random.default_rng(case.noise_seed)
        self.last_tick = None
        self.noise_block = -1
        self.noise = np.zeros((1, 2), dtype=np.float64)

    def apply(self, prediction, elapsed_ticks):
        action = np.asarray(prediction, dtype=np.float32)
        if action.shape != (1, 2) or not np.isfinite(action).all():
            raise ValueError("Expected one finite normalized two-axis prediction")
        if (not isinstance(elapsed_ticks, int) or isinstance(elapsed_ticks, bool)
                or elapsed_ticks < 0):
            raise ValueError("Invalid physical evaluation clock")
        if self.last_tick is None:
            if elapsed_ticks != 0:
                raise ValueError("Evaluation clock must start at zero")
        elif not self.last_tick < elapsed_ticks <= self.last_tick + self.hold_ticks:
            raise ValueError("Evaluation clock regressed or skipped a perturbation block")
        warmup_ticks = len(self.warmup) * self.hold_ticks
        if elapsed_ticks < warmup_ticks:
            applied = self.warmup[elapsed_ticks // self.hold_ticks][None, :].copy()
        else:
            block = (elapsed_ticks - warmup_ticks) // self.hold_ticks
            if block != self.noise_block:
                if block != self.noise_block + 1:
                    raise ValueError("Skipped a physical noise block")
                if self.case.action_noise_std:
                    self.noise = self.rng.normal(0, self.case.action_noise_std, action.shape)
                self.noise_block = block
            applied = np.clip(action + self.noise, -1, 1).astype(np.float32)
        self.last_tick = elapsed_ticks
        return applied
