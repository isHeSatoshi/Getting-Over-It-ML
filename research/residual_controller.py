"""Explicit causal residual scaffold, not a trained policy or a teacher."""
from copy import deepcopy
import math

import numpy as np

from research.demonstrations import require
from research.stroke_controller import StrokeController, contract as base_contract

VERSION = "explicit-context-residual-stroke-v1"
RAW_DIMENSION = 217
ACTOR_DIMENSION = 222
RESIDUAL_SCALE = 2.0
HORIZON = 1800
MODE = "contact_timed_feedback"


def contract():
    return {
        "version": VERSION, "base": base_contract(MODE),
        "raw_dimension": RAW_DIMENSION, "actor_dimension": ACTOR_DIMENSION,
        "actor_dtype": "float32",
        "actor_layout": ["raw217", "selected_source_phase/599",
                         "current_base_proposal_x", "current_base_proposal_y",
                         "previous_own_issued_final_x", "previous_own_issued_final_y"],
        "residual_scale": RESIDUAL_SCALE, "residual_axes": [-1, 1],
        "action": "float32clip(baseproposal + 2*legal_residual, -1, 1)",
        "clock": "One unchanged base call per prepared actual transition, min(calls,599); "
                 "cached preparation never advances twice. frame_skip=1, horizon=1800.",
        "history": "Previous OWN issued final command, initially zeros, never substituted "
                   "with desired base proposal or externally perturbed applied command.",
        "alignment": "reset(actualraw), prepare(actualpre), action(legalresidual), "
                     "observe(actualpost,actualapplied,terminal,truncated); next pre equals post",
        "normalization": "Fresh matching222 RMS/checkpoint contract; reject old217 normalizers. "
                         "Normalize only actor input, never raw input to the base controller.",
        "maximum_transitions": HORIZON, "frame_skip": 1,
        "ordinary_start": True, "privileged_reset": False,
        "privileged_counter_input": False, "teacher_data_admission": False, "learning_updates": 0,
        "limit": "Zero residual is the hand-designed baseline, never learned progress. "
                 "No environment/physics/reward edits or optimizer. Learned benefit must beat "
                 "this same baseline; proposals/clipped/ignored controls are not teacher labels.",
    }


def validate_normalizer(rms, saved_contract):
    """Reject mismatched actor schemas before any future saved-policy inference."""
    require(saved_contract == contract(), "Residual checkpoint contract mismatch")
    mean, variance = np.asarray(rms.mean), np.asarray(rms.var)
    require(mean.shape == variance.shape == (ACTOR_DIMENSION,)
            and np.isfinite(mean).all() and np.isfinite(variance).all()
            and (variance >= 0).all() and math.isfinite(float(rms.count))
            and float(rms.count) > 0, "Residual actor needs a matching finite222 RMS")


def _raw(observation):
    observation = np.asarray(observation)
    require(observation.shape == (RAW_DIMENSION,) and observation.dtype == np.float32
            and np.isfinite(observation).all(), "Residual scaffold needs raw217float32 inputs")
    require(observation[22] in (0, 1) and observation[19] >= 0,
            "Residual base needs raw query flag and nonnegative travel")
    return observation


def _command(command):
    command = np.asarray(command)
    require(command.shape == (2,) and command.dtype == np.float32
            and np.isfinite(command).all() and np.abs(command).max() <= 1,
            "Expected one legal two-axis float32 command")
    return command


class ResidualController:
    """A strict per-tick lifecycle with all extra policy context visible."""

    def __init__(self, observations, actions):
        self._base = StrokeController(observations, actions, MODE)
        self._state, self._reason = "uninitialized", None
        self._steps = 0
        self._post = self._pre = self._context = self._proposal = None
        self._own = np.zeros(2, np.float32)
        self._residual = self._unclipped = self._issued = self._applied = None
        self._last_transition = None

    def reset(self, actual_observation):
        """Caller must have actually reset the environment; no state placement."""
        observation = _raw(actual_observation)
        require(-180 <= float(observation[1])*16000 <= 16000, "Reset input is terminal")
        self._base.reset()
        self._state, self._reason, self._steps = "ready", None, 0
        self._post = observation.copy()
        self._pre = self._context = self._proposal = None
        self._own = np.zeros(2, np.float32)
        self._residual = self._unclipped = self._issued = self._applied = None
        self._last_transition = None

    def prepare(self, actual_pre):
        observation = _raw(actual_pre)
        require(self._state in ("ready", "prepared"), "No ready residual transition")
        require(np.array_equal(observation, self._post), "Pre-input differs from last actual post")
        if self._state == "prepared":
            return self._context.copy()
        require(self._steps < HORIZON and self._base.calls == self._steps,
                "Residual source clock or horizon mismatch")
        require(-180 <= float(observation[1])*16000 <= 16000, "Pre-input is terminal")
        self._proposal = self._base.action(observation).copy()
        self._pre = observation.copy()
        extra = np.asarray([self._base.phase/599, *self._proposal, *self._own], np.float32)
        self._context = np.concatenate((self._pre, extra))
        self._residual = self._unclipped = self._issued = self._applied = None
        self._state = "prepared"
        return self._context.copy()

    def action(self, residual):
        residual = _command(residual)
        require(self._state == "prepared", "Prepare one actual pre-input before residual action")
        self._residual = residual.copy()
        self._unclipped = self._proposal + np.float32(RESIDUAL_SCALE)*self._residual
        self._issued = np.clip(self._unclipped, -1, 1).astype(np.float32)
        self._state = "issued"
        return self._issued.copy()

    def observe(self, actual_post, actual_applied, *, terminated=False, truncated=False):
        observation, applied = _raw(actual_post), _command(actual_applied)
        require(isinstance(terminated, bool) and isinstance(truncated, bool),
                "Actual termination flags must be explicit booleans")
        require(self._state == "issued", "No pending residual action for this post-input")
        self._applied = applied.copy()
        self._post, self._own = observation.copy(), self._issued.copy()
        self._steps += 1
        self._reason = None
        if terminated or not -180 <= float(observation[1])*16000 <= 16000:
            self._reason = "terminal"
        elif truncated:
            self._reason = "environment_truncated"
        elif self._steps == HORIZON:
            self._reason = "horizon"
        self._state = "finished" if self._reason else "ready"
        self._last_transition = {
            "pre_observation": self._pre.tolist(), "actor_input": self._context.tolist(),
            "base_proposal": self._proposal.tolist(), "legal_residual": self._residual.tolist(),
            "unclipped_final": self._unclipped.tolist(), "final_issued": self._issued.tolist(),
            "actual_applied": self._applied.tolist(), "actual_post": self._post.tolist(),
            "final_clip_changed": bool(not np.array_equal(self._unclipped, self._issued)),
            "external_application_changed": bool(not np.array_equal(self._issued, self._applied)),
            "source_phase": self._base.phase, "source_calls": self._base.calls,
            "actual_transitions": self._steps, "terminated": terminated, "truncated": truncated,
            "teacher_label": False,
        }
        return self.summary()

    def base_summary(self):
        return deepcopy(self._base.last)

    def summary(self):
        return {
            "version": VERSION, "state": self._state, "reason": self._reason,
            "steps": self._steps, "base_calls": self._base.calls, "base_phase": self._base.phase,
            "previous_own_final": self._own.tolist(), "finished": self._state == "finished",
            "last_transition": deepcopy(self._last_transition),
        }
