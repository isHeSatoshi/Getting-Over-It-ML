"""State-matched legal trajectory prior, experimental controller not an oracle."""
import hashlib
from pathlib import Path

import numpy as np
from stable_baselines3.common.running_mean_std import RunningMeanStd

from research.demonstrations import load, require
from research.env import BASE_FEATURES
from research.provenance import fingerprint

VERSION = "state-matched-trajectory-phase-v1"
SOURCE_DATA_SHA = "f97fdda3397e432d1dbf586fe1055cdfb94ef81172d1962378a8559892b88537"
SOURCE_OBSERVATION_SHA = "de89f841bafe175a7dceda293c53403a51b0e41a444994043e01f80a55df2d17"
SOURCE_ACTION_SHA = "5f969f824db978234c004186e3b13afafb5662705f424553eb39160c104fa4e7"
FEATURES = ("world_x", "altitude", "body_dx", "body_dy", "hammer_offset_x", "hammer_offset_y",
            "hammer_dx", "hammer_dy", "angle_sin", "angle_cos", "angular_delta",
            "body_collision", "hammer_collision")
INDICES = np.asarray([BASE_FEATURES.index(name) for name in FEATURES])
HISTORY_FEATURES = ("pointer_x", "pointer_y", "last_tx", "last_ty", "control_memory_x",
                    "control_memory_y", "last_hammer_distance", "last_effort")
FEATURE_SETS = {"kinematic": FEATURES, "control_history": FEATURES + HISTORY_FEATURES}


def contract(feature_set="kinematic"):
    require(feature_set in FEATURE_SETS, "Unknown fixed phase-matching feature set")
    return {
        "version": (VERSION if feature_set == "kinematic" else "state-matched-control-history-v2"),
        "source_data_sha256": SOURCE_DATA_SHA,
        "nominal_pre_observations_sha256": SOURCE_OBSERVATION_SHA,
        "nominal_applied_actions_sha256": SOURCE_ACTION_SHA,
        "source_rows": 600, "input": "Raw legal217feature pre-action float32 observations only",
        "distance_features": list(FEATURE_SETS[feature_set]), "position_squared_distance_weight": 4.0,
        "other_squared_distance_weight": 1.0,
        "normalization": "Original3576eligible-row RMS; clipped10,epsilon1e-8, no refitting",
        "backtrack_rows": 8, "lookahead_rows": 12, "first_phase": 0,
        "phase_update": "Nearest observed state within the bounded previous-phase window; "
                        "no unconditional time advance or hidden elapsed-tick input",
        "tie_break": "Earliest index in local window",
        "action": "Actually applied nominal demonstration control at selected phase, float32 clipped[-1,1]",
        "ordinary_start": True, "privileged_reset": False, "learning_updates": 0,
        "limit": "Nearest recorded state is a prior, not proof of corrective target validity. "
                 "Only new actual physical application can test recovery; no training corpus or oracle claim.",
    }


def load_prior(directory, current=None):
    arrays, record = load(Path(directory), fingerprint() if current is None else current)
    require(record["data_sha256"] == SOURCE_DATA_SHA and int(arrays["eligible"].sum()) == 3576,
            "Changed verified demonstration source")
    selected = arrays["episode_ids"] == 0
    observations, actions = arrays["observations"][selected], arrays["actions"][selected]
    episode = record["episodes"][0]
    require(episode["case"]["name"] == "demo_nominal" and episode["warmup_ticks"] == 0
            and arrays["eligible"][selected].all() and len(observations) == 600,
            "Expected the validated ordinary-spawn nominal trajectory")
    require(hashlib.sha256(observations.tobytes()).hexdigest() == SOURCE_OBSERVATION_SHA
            and hashlib.sha256(actions.tobytes()).hexdigest() == SOURCE_ACTION_SHA,
            "Changed nominal pre-state/control alignment")
    rms = RunningMeanStd(shape=(217,))
    rms.update(arrays["observations"][arrays["eligible"]])
    return observations, actions, rms


class PhaseController:
    def __init__(self, observations, actions, rms, mode="state_matched", *, feature_set="kinematic"):
        require(mode in ("state_matched", "time_indexed"), "Unknown phase-controller mode")
        require(feature_set in FEATURE_SETS, "Unknown fixed phase-matching feature set")
        observations, actions = np.asarray(observations), np.asarray(actions)
        require(observations.shape == (600, 217) and actions.shape == (600, 2)
                and observations.dtype == actions.dtype == np.float32
                and np.isfinite(observations).all() and np.isfinite(actions).all()
                and np.abs(actions).max() <= 1, "Invalid legal trajectory prior")
        require(rms.mean.shape == rms.var.shape == (217,) and np.isfinite(rms.mean).all()
                and np.isfinite(rms.var).all() and (rms.var >= 0).all(),
                "Invalid fixed observation scale")
        self.mode = mode
        self.feature_set = feature_set
        self.indices = np.asarray([BASE_FEATURES.index(name) for name in FEATURE_SETS[feature_set]])
        self.mean, self.variance = rms.mean.copy(), rms.var.copy()
        self.references = self._features(observations).copy()
        self.actions = actions.copy()
        self.weights = np.asarray([4, 4] + [1]*(len(self.indices)-2), dtype=np.float64)
        self.reset()

    def _features(self, observations):
        return np.clip((observations[..., self.indices] - self.mean[self.indices])
                       / np.sqrt(self.variance[self.indices] + 1e-8), -10, 10)

    def reset(self):
        self.phase, self.calls = 0, 0
        self.last = None

    def action(self, observation):
        observation = np.asarray(observation)
        require(observation.dtype == np.float32 and observation.shape == (217,)
                and np.isfinite(observation).all(), "Controller requires the raw pre-action217float32 input")
        require(self.calls < 1800, "Prototype controller call budget exhausted")
        previous = self.phase
        if self.mode == "time_indexed":
            chosen, distance = min(self.calls, 599), None
            start = stop = None
        else:
            start, stop = max(0, previous-8), min(600, previous+13)
            difference = self.references[start:stop] - self._features(observation)
            squared = np.sum(difference*difference*self.weights, axis=1)
            offset = int(np.argmin(squared))
            chosen, distance = start+offset, float(np.sqrt(squared[offset]))
        self.phase = chosen
        self.calls += 1
        self.last = {"mode": self.mode, "previous_phase": previous, "selected_phase": chosen,
                     "candidate_start": start, "candidate_stop_exclusive": stop,
                     "normalized_feature_distance": distance, "calls": self.calls}
        return self.actions[chosen].copy()
