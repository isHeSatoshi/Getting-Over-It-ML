"""Ordered observable stroke completion with bounded legal pointer correction."""
import numpy as np

from research.demonstrations import require
from research.env import BASE_FEATURES
from research.phase_controller import contract as prior_contract

VERSION = "observable-stroke-world-feedback-v1"
POSITION = np.asarray([BASE_FEATURES.index(name) for name in
                       ("world_x", "altitude", "hammer_offset_x", "hammer_offset_y")])
VELOCITY = np.asarray([BASE_FEATURES.index(name) for name in
                       ("body_dx", "body_dy", "hammer_dx", "hammer_dy")])
TUBE_PIXELS = 26.0
STATIC_POSITION_PIXELS = 1.0
STATIC_SPEED_PER_TICK = 2.0
CORRECTION_CAP_PIXELS = 16.0


def contract():
    source = prior_contract()
    return {
        "version": VERSION,
        **{key: source[key] for key in ("source_data_sha256", "nominal_pre_observations_sha256",
                                      "nominal_applied_actions_sha256", "source_rows")},
        "input": "Raw217float32 pre-action observation and private resettable stroke phase only",
        "positions": "Body(world_x*5500,altitude*16000); hammer=body+offset*102",
        "progress": "At most one forward row after previous action: projection past next body/hammer "
                    "world-position segment endpoint and perpendicular distance<=26pixels. "
                    "No nearest-state search, phase backtracking or unconditional clock advance.",
        "moving_segment_epsilon": 1e-8, "projection_completion_threshold": 1.0 - 1e-6,
        "perpendicular_tube_pixels": TUBE_PIXELS,
        "stationary_completion": "Both body/hammer within1pixel of next reference and "
                                 "both observed speeds<=2pixels/tick",
        "stationary_position_pixels": STATIC_POSITION_PIXELS,
        "stationary_max_speed_per_tick": STATIC_SPEED_PER_TICK,
        "first_phase": 0, "maximum_phase": 599, "maximum_controller_calls": 1800,
        "correction": "Prior pointer + (reference body - actual body), norm-clipped16pixels, "
                      "then pointer axes clipped[-128,128] and float32 action/128",
        "position_gain": 1.0, "correction_norm_cap_pixels": CORRECTION_CAP_PIXELS,
        "servo_basis": "Original request0.4*(pointer-hammer+body+render_offset). "
                      "Body-error correction approximately preserves a world hammer target; "
                      "not an inverse contact solver or a guaranteed corrective target.",
        "ordinary_start": True, "privileged_reset": False, "learning_updates": 0,
        "limit": "Experimental causal feedback, not validated teacher, labels or learned policy. "
                 "Actual physical nominal and perturbed recovery must precede any data admission.",
    }


def points(observations):
    scaled = np.asarray(observations[..., POSITION], dtype=np.float64)
    body = scaled[..., :2] * (5500, 16000)
    hammer = body + scaled[..., 2:] * 102
    return np.concatenate((body, hammer), axis=-1)


class StrokeController:
    def __init__(self, observations, actions):
        observations, actions = np.asarray(observations), np.asarray(actions)
        require(observations.shape == (600, 217) and actions.shape == (600, 2)
                and observations.dtype == actions.dtype == np.float32
                and np.isfinite(observations).all() and np.isfinite(actions).all()
                and np.abs(actions).max() <= 1, "Invalid legal stroke prior")
        self.references, self.actions = points(observations).copy(), actions.copy()
        self.reset()

    def reset(self):
        self.phase, self.calls, self.last = 0, 0, None

    def action(self, observation):
        observation = np.asarray(observation)
        require(observation.shape == (217,) and observation.dtype == np.float32
                and np.isfinite(observation).all(), "Stroke controller needs raw217float32 input")
        require(self.calls < 1800, "Stroke controller call budget exhausted")
        current, previous = points(observation), self.phase
        reached, progress, perpendicular = False, None, None
        if self.calls and self.phase < 599:
            start, endpoint = self.references[self.phase:self.phase+2]
            segment = endpoint - start
            squared_length = float(segment @ segment)
            if squared_length > 1e-8:
                progress = float((current - start) @ segment / squared_length)
                perpendicular = float(np.linalg.norm(current - (start + progress*segment)))
                reached = progress >= 1.0 - 1e-6 and perpendicular <= TUBE_PIXELS
            else:
                errors = (current - endpoint).reshape(2, 2)
                speeds = np.asarray(observation[VELOCITY], dtype=np.float64).reshape(2, 2)*64
                reached = (np.linalg.norm(errors, axis=1).max() <= STATIC_POSITION_PIXELS
                           and np.linalg.norm(speeds, axis=1).max() <= STATIC_SPEED_PER_TICK)
            if reached:
                self.phase += 1
        correction = self.references[self.phase, :2] - current[:2]
        magnitude = float(np.linalg.norm(correction))
        if magnitude > CORRECTION_CAP_PIXELS:
            correction *= CORRECTION_CAP_PIXELS / magnitude
        pointer = np.asarray(self.actions[self.phase], dtype=np.float64)*128 + correction
        action = (np.clip(pointer, -128, 128)/128).astype(np.float32)
        self.calls += 1
        self.last = {"mode": "stroke_feedback", "previous_phase": previous,
                     "selected_phase": self.phase, "observed_completion": bool(reached),
                     "segment_progress": progress, "perpendicular_distance_pixels": perpendicular,
                     "pointer_correction_pixels": correction.tolist(), "calls": self.calls}
        return action
