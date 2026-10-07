"""Predeclared held-out controller perturbations, all using legal mouse actions."""
from dataclasses import asdict, dataclass
import numpy as np


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    reset_seed: int
    warmup: tuple = ()
    action_noise_std: float = 0.0
    noise_seed: int = 0

    def describe(self):
        return asdict(self)


STANDARD_CASES = (
    EvaluationCase("nominal", 1001),
    EvaluationCase("hammer_left", 1001, ((-0.5, 0.5),) * 3),
    EvaluationCase("hammer_right", 1001, ((0.5, 0.5),) * 3),
    *(EvaluationCase(f"action_noise_{i}", 1001, action_noise_std=0.02, noise_seed=8100 + i)
      for i in range(6)),
)


def perturb(action, case, rng):
    action = np.asarray(action, dtype=np.float32)
    if case.action_noise_std:
        action = action + rng.normal(0, case.action_noise_std, action.shape)
    return np.clip(action, -1, 1).astype(np.float32)
