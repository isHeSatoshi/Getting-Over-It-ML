"""State-matched demonstration actions for exploration seeding only.

The matcher never scores or evaluates the policy. It supplies demonstration
actions as exploration during training so the replay contains the coordinated
swing motions that pure Gaussian exploration (sigma~0.09 at target entropy -2)
cannot sample; the demo's own actions have sigma~0.5. Evaluation remains
learned-only with no teacher actions, unchanged gates.
"""
import numpy as np

from research.demonstrations import require

FEATURES = ("world_x", "altitude", "body_dx", "body_dy", "hammer_offset_x", "hammer_offset_y",
            "hammer_dx", "hammer_dy", "angle_sin", "angle_cos", "angular_delta",
            "body_collision", "hammer_collision")


class DemoActionMatcher:
    def __init__(self, observations, actions, rms, threshold):
        from research.env import BASE_FEATURES
        observations = np.asarray(observations)
        actions = np.asarray(actions)
        require(observations.shape == (600, 217) and observations.dtype == np.float32
                and np.isfinite(observations).all(), "Demo matcher needs the 600-tick raw217 prior")
        require(actions.shape == (600, 2) and actions.dtype == np.float32
                and np.isfinite(actions).all() and np.abs(actions).max() <= 1,
                "Demo matcher needs legal float32 prior actions")
        require(type(threshold) is float and 0 < threshold <= 50, "Invalid demo match threshold")
        require(rms.mean.shape == (217,) and rms.var.shape == (217,)
                and np.isfinite(rms.mean).all() and (rms.var >= 0).all(), "Invalid demo scale")
        self.indices = np.asarray([BASE_FEATURES.index(name) for name in FEATURES])
        self.weights = np.asarray([4, 4] + [1]*(len(self.indices)-2), np.float64)
        self.mean, self.variance = rms.mean.copy(), rms.var.copy()
        self.actions = actions.copy()
        self.threshold = threshold
        self.references = self._features(observations).copy()

    def _features(self, observations):
        values = np.asarray(observations)[..., self.indices]
        return np.clip((values - self.mean[self.indices]) / np.sqrt(self.variance[self.indices] + 1e-8),
                       -10, 10)

    def seed_action(self, raw):
        """Return (demo action, distance) near the demo route, else (None, distance)."""
        raw = np.asarray(raw)
        require(raw.dtype == np.float32 and raw.shape == (217,) and np.isfinite(raw).all(),
                "Demo seeding requires actual raw217float32")
        difference = self.references - self._features(raw)
        squared = np.sum(difference*difference*self.weights, axis=1)
        index = int(np.argmin(squared))
        distance = float(np.sqrt(squared[index]))
        if distance > self.threshold:
            return None, distance
        return self.actions[index].copy(), distance
