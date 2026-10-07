"""Reference baselines.

`NullPolicy` does nothing and must score zero on every tier. It is the control
that proves the region detector is not awarding points for free.

`ConstantPushPolicy` reproduces the documented causal check: hold the pointer
at (0, -128). Measured on the reference runtime it lifts the body from
world Y=21 to about Y=86. It is not a climb and must not be submitted as one.
"""
import numpy as np

from challenge.env import describe  # noqa: F401  (re-exported for submitters)


class NullPolicy:
    """Always emits (0, 0). Should never reach any tier."""

    def reset(self):
        pass

    def action(self, observation):
        return np.zeros(2, dtype=np.float32)


class ConstantPushPolicy:
    """Hold a fixed player-relative pointer offset."""

    def __init__(self, x=0.0, y=-128.0):
        self.target = np.asarray([x, y], dtype=np.float32) / 128.0

    def reset(self):
        pass

    def action(self, observation):
        return self.target.copy()


class ScriptedPolicy:
    """Replay a fixed per-decision action sequence, then hold the last one.

    Useful for checking that the harness faithfully reproduces a recorded
    physical trajectory.
    """

    def __init__(self, actions):
        actions = np.asarray(actions, dtype=np.float32)
        if actions.ndim != 2 or actions.shape[1] != 2 or len(actions) == 0:
            raise ValueError("ScriptedPolicy needs a non-empty (N, 2) action array")
        if not np.isfinite(actions).all() or np.abs(actions).max() > 1.0:
            raise ValueError("Scripted actions must be finite and inside [-1, 1]")
        self.actions = actions
        self.index = 0

    def reset(self):
        self.index = 0

    def action(self, observation):
        action = self.actions[min(self.index, len(self.actions) - 1)]
        self.index += 1
        return np.asarray(action, dtype=np.float32)
