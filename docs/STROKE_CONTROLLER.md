# Ordered stroke-feedback diagnostic

`research/stroke_controller.py` is a non-learning experiment, not a validated
teacher. It uses the same hash-bound 600-row nominal prior as the phase
controller. Only legal raw 217-feature pre-action inputs enter the controller.
Private phase and call count reset with every episode.

## Original motor and proposed feedback

Original Scratch Player blocks `bF`/`bG` request
`0.4 * (pointer - hammer_world + body_world + render_offset)`.
The original 40-unit change limit, 50-unit motor limit, 26..102 reach and
collision solver remain untouched. Thus a pointer command already drives an
inner position servo. Holding one recorded row need not complete a stroke.

The prototype reconstructs body and hammer world positions from the existing
observation. After issuing a row, it advances at most one row when the current
four-coordinate position projects past the next reference segment endpoint,
within a fixed 26-pixel perpendicular tube. A stationary segment instead
requires both points within 1 pixel and both observed speeds at most 2 pixels
per tick. No nearest-row search, backward phase step, timeout-driven jump or
unconditional clock advance.

The pointer receives a gain-1 correction equal to reference body position
minus actual body position, norm-capped at 16 pixels. Final axes stay within
128 pixels and output remains normalized float32. This approximately keeps a
world hammer target despite body displacement. It is not a contact-model
inverse and does not establish a corrective label.

## Frozen original-physics comparison

Both offline nominal input/action/phase parity and the actual nominal
600-tick physics trace are exact. The prototype holds central and secondary
regions at `(322.586,104)`, retained gain 83, with zero correction.

| Case | Timed recording | Ordered stroke feedback |
|---|---|---|
| Left warm-up | Central and secondary holds, gain 83 | No hold, `(59.448,20.770)`, gain -0.230, phase 58 |
| Noise11105 | Secondary only, gain 82 | No hold, `(169.478,29)`, gain 8, phase 173 |

Both perturbed final 120-tick phase ranges are constant. Correction is genuinely
exercised after warm-up/noise on 564/572 ticks, respectively. Maximum correction
norm is 8.367/16 pixels (round-off in the latter is below `1e-12`).
The final warm-up projection is -15.675; the noisy projection is 0.93964 and
perpendicular distance 27.393, so neither completion gate advances.
These are descriptions of the stalled gates, not proof that either one alone
caused failure. Progress gating and action correction changed together.

Twelve rollouts, 7200 controlled and 1440 reset ticks, no optimizer updates,
summits or deaths. All six full reference/fast pairs and all six pinned
historical timed baselines agree exactly. Independent review reconstructs
every milestone field from raw position, velocity and body-contact telemetry,
and rechecks every proposed/applied action and physical perturbation clock.
All 307 Python tests and collision checks pass.
Evidence: `artifacts/stroke_feedback_probe_20261004T202114143143Z/verification.json`.

Reject this recipe for corrective teaching or new training data. Keep only
the tested diagnostic tooling and evidence. Next freeze one ablation: retain
the exact body-error correction and bounds, but use the declared physical
playback clock instead of stroke-completion gating. This is explicitly timed
feedback, not observed-state phase acquisition. Compare with pure playback
on the same development cases, with no gain/tube/cap sweep, and require actual
recovery plus fidelity before broader teacher validation or learning.
