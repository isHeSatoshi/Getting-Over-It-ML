# Ordered stroke-feedback diagnostic

`research/stroke_controller.py` is a non-learning experiment, not a validated
teacher. It uses the same hash-bound 600-row nominal prior as the phase
controller. Only legal raw 217-feature pre-action inputs enter the controller.
Private phase and call count reset with every episode. The default remains
`mode="stroke_feedback"`; the opt-in clock ablation is described separately.

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
the tested diagnostic tooling and evidence. The following ablation retained
the exact body-error correction and bounds, but used the declared physical
playback clock instead of stroke-completion gating. This is explicitly timed
feedback, not observed-state phase acquisition. Compare with pure playback
on the same development cases, with no gain/tube/cap sweep, and require actual
recovery plus fidelity before broader teacher validation or learning.

## Explicit-clock ablation

`mode="timed_feedback"` selects `min(one-tick decision calls,599)`. The clock
advances through legal forced warm-up inputs exactly as pure playback does.
It is explicitly timed feedback, not observed-state phase acquisition.
The same correction code, gain 1, 16-pixel norm cap, 128-pixel axis limits,
prior and cases remain fixed. Completion-gate settings remain recorded but
are inactive in this mode.

Both modes preserve 600 offline nominal action/phase pairs. The original
default also reproduces all 3600 logged action/metadata pairs unchanged.
Nominal physical controls and observations remain identical to playback.

| Case | Pure playback | Explicit-clock feedback |
|---|---|---|
| Nominal | Central and secondary holds, gain 83 | Identical |
| Left warm-up | Central and secondary holds, gain 83 | Both holds, `(319.942,104)`, gain 83 |
| Noise11105 | Secondary only, `(335.292,103)`, gain 82 | No hold, `(208.585,82.027)`, gain 61.027 |

Removing stroke gating restores the selected warm-up hold, but this correction
harms the noisy playback case. Feedback acts after interventions on 579/573
ticks. All cases reach phase 599, so that noisy failure is not phase stalling.
The fixed three-case central gate still fails. These reused development cases
do not establish general robustness or justify teaching or label admission.

Twelve rollouts, 7200 control and 1440 reset ticks, zero updates, summits or
deaths. All six full backend pairs and historical playback baselines are
exact. Independent review reconstructs every raw milestone and verifies every
control, perturbation and explicit-clock row. All 311 Python tests and
collision checks pass.
Evidence: `artifacts/timed_feedback_probe_20261004T203929123127Z/verification.json`.

Reject this fixed world/body-error correction as a teacher. Next audit the
first harmful corrective segment and the original planted-hammer-to-body
response before proposing a contact-aware rule. Use existing captured traces;
do not launch another gain/cap/tube sweep or assume that a query hit is a force
measurement. Any new feedback rule needs a fresh frozen physical test before
teacher validation, training data or paid learning.

## Offline planted-response audit

No new gameplay or training. Twelve captured traces, 7200 rows, remain
hash-bound to the closed clock ablation. The nominal streams are identical.

The noisy streams share the first 27 legal applied controls and full physical
states. At controlled tick 28, raw pre-inputs still match exactly, but feedback
adds `(-0.490001,-0.569308)` pointer pixels. The actual pointer difference is
`(-0.490,-0.570)` after the game's input reporting. The hammer does not move
differently, while the body moves an extra `(+0.098,+0.114)` pixels, opposite
the intended correction. The previous hammer query-hit is true and previous
hammer travel is zero.

Original `move hammer` blocks `f`/`b{` contain a blocked branch that calls body
motion with `-0.5 * requested_hammer_motion`. Combined with motor gain 0.4,
the observed first response is consistent with a `-0.2` local body response
to pointer change. This is evidence of one same-prefix response reversal,
not proof that every later failure has that cause.

Warm-up first proposed controls differ at tick 2, but forced inputs mask the
change until tick 14. The exact common applied-control/state prefix is 13
ticks. At the first applied contrast, previous query hit is false, previous
hammer travel is 37.203 pixels, the hammer moves differently and body motion
does not. Do not treat ignored warm-up proposals as applied corrections.

Noisy body separation exceeds 1 pixel at tick 30; query-hit flags first differ
at tick 285. Warm-up counterparts are ticks 32 and 61. Later inputs are already
unequal, so these milestones describe divergence, not isolated causal effects.
An aggregate query-hit flag does not expose the current internal wall-test
branch, contact normal, force, or whether the hammer will remain planted.
Evidence: `artifacts/contact_response_audit_20261004T205819078549Z/verification.json`.

Next hypothesis: retain explicit clock, prior, gain and bounds, but reverse
the correction only when the causal pre-input has a hammer query hit and
previous hammer travel below the original 3-pixel wall-test threshold.
Treat this as a fallible observable proxy, not the true solver branch.
First freeze a legal recorded-prefix, one-step sign check on both backends
from ordinary spawn, with no state placement. Only a verified intended local
response can admit the next fixed-case recovery check; neither stage admits
teacher labels or learning automatically. No sign/threshold/gain sweep.

## Same-prefix contact-sign check

Opt-in `mode="contact_timed_feedback"` changes only correction sign. It uses
the existing explicit clock and reverses the body-error pointer correction
when raw previous hammer query-hit is exactly 1 and raw previous hammer
travel is below 3 pixels. Gain 1, norm cap 16, legal axis cap 128 and prior
remain fixed. Proxy inputs must be raw binary/nonnegative values. The default
and earlier timed modes remain unchanged.

All three modes reproduce the 600 nominal recorded action/phase pairs.
Earlier modes reproduce all 7200 captured action/metadata rows unchanged.
The new ordinary-spawn diagnostic first revalidates the 600-tick nominal
playback central hold on reference and fast. It then replays legal common
prefixes and compares pure playback, old correction and contact-sign
correction for just one step at warm-up tick 14 and noisy tick 28.
Prefix candidate proposals are explicitly overridden by recorded controls;
they are not claimed candidate-policy behavior or training labels.

At the identical noisy pre-input, the old correction adds body motion
`(+0.098,+0.114)` relative to playback. The new correction instead adds
`(-0.098,-0.1138)`, with zero hammer displacement difference. Response dotted
with intended body error changes from -0.112921 to +0.112807. The proxy is
active. In the free-motion warm-up state it is inactive, with exactly the same
action and response as the old correction. The declared local sign gate passes.

Fourteen rollouts, 1452 controlled and 1680 reset ticks, zero updates, summits
or deaths. All seven full backend pairs are exact. Legal prefixes and old
final-step baselines reproduce exactly. Independent review reconstructs all
raw milestone traces, proposed-versus-applied controls and perturbation
clocks, and recomputes the local response gate. All 315 Python tests and
collision checks pass.
Evidence: `artifacts/contact_sign_probe_20261004T212005018592Z/verification.json`.

Zero new-controller full closed-loop recovery cases were evaluated. The only
ledge acquisition here is the existing nominal playback baseline. A positive
one-step effect is not a teacher, saved policy, recovery or summit.
Next freeze one full diagnostic: pure playback, unchanged timed feedback and
contact-sign timed feedback, the same three development cases, 600 ticks each,
both backends, with no rule/threshold/gain/cap changes. Require nominal exact
replay and actual perturbed holds before any broader teacher validation.
No automatic corpus or learning admission even if those three cases pass.

## Full fixed-case recovery check

The rule is unchanged from the local sign check. All candidate proposals
after the declared forced warm-up are applied through the fixed noise clock,
with no recorded-prefix overrides. The three-arm comparison runs pure
playback, old timed feedback and contact-sign timed feedback for 600 ticks
on each of the same three development cases, on both backends.

| Case | Pure playback central/secondary | Old feedback central/secondary | Contact-sign central/secondary |
|---|---|---|---|
| Nominal | Yes / Yes, gain 83 | Yes / Yes, gain 83 | Yes / Yes, gain 83 |
| Left warm-up | Yes / Yes, gain 83 | Yes / Yes, gain 83 | Yes / Yes, gain 83 |
| Noise11105 | No / Yes, gain 82 | No / No, gain 61.027 | Yes / Yes, gain 83 |

Candidate final positions are `(322.586,104)`, `(322.586,104)` and
`(330.225,104)`. Every final 90-tick body window stays inside the unchanged
central region, with body-query contact fraction 1 and maximum speed
0, 0 and 0.44524 pixels/tick. These are final supported holds, not merely
latched earlier events. Warm-up/noise corrected ticks are 579/573, including
142/139 nonzero contact-reversed corrections. Nominal corrections are zero.

The development gate passes: all three reference central holds, exact nominal
replay, exercised feedback/sign reversal and exact full backend traces.
All twelve old playback/feedback traces reproduce exactly. Eighteen rollouts,
10800 control and 2160 reset ticks, zero updates, summits or deaths.
Independent review reconstructs every raw milestone/control/clock field and
final support window. Twenty-six focused Python tests and collision checks
pass; the controller's last full 315-test suite remains unchanged.
The owned study finishes in 73.85 seconds within its frozen 300-second bound.
Evidence: `artifacts/contact_recovery_probe_20261004T213808503161Z/verification.json`.

This admits broader fresh perturbation validation only. It is a hand-designed,
clock-guided controller, not learned-policy improvement or a corrective
teacher established across states. No new training corpus or paid learning.

Next freeze two arms, pure playback and this exact contact-sign rule, on nine
new development-validation cases: reset 13001, nominal, legal left/right
`(+/-0.875,0.125)` warm-ups repeated three times (four ticks each), and six
noise streams 12100..12105 with standard deviation 0.02. Use 600 ticks and both
backends, maximum 36 rollouts/21600 control/4320 reset, 300-second work bound.
Require all nine reference central final supported holds, no deaths, nominal
parity and exact backend fidelity before even considering corrective-data
admission. New cases are not final held-out learned-policy tests. No retuning
or label collection during validation; passing still needs a distinct data
and learner contract that handles the controller's explicit clock honestly.

## Fresh nine-case validation

The frozen rule was not changed. Reset 13001, stronger left/right warm-ups
and noise seeds 12100..12105 were verified unused before declaration.
All 36 actual 600-tick runs completed on reference and fast.

| Reference arm | Central final holds | Secondary holds | Retained height |
|---|---:|---:|---|
| Pure playback | 5/9 | 6/9 | 63.697..83 pixels |
| Contact-sign feedback | 8/9 | 9/9 | 83 pixels in every case |

Nominal and both stronger warm-ups end centrally at Y104. Noise streams
12101..12105 also finish centrally, at X322.016..325.548. Noise12100 instead
ends at `(293.728,104)`: the final 90-tick body window remains supported in
the secondary region, with contact fraction 1, maximum speed 0.46138 and
Y103.539..104. X is constant and below the unchanged central minimum 305.
No deaths or summits.

The strict 9/9 central-final-support gate fails. Do not promote 8/9 as a
retrospective pass or relax the detector. The controller materially improves
these cases versus playback, but remains a hand-designed clock-guided prior,
not a learned policy or admitted corrective teacher. All traces remain
diagnostic, with no training corpus or learner updates.

21600 controlled and 4320 reset ticks. All eighteen full backend pairs and
four historical nominal traces are exact. Independent review reconstructs
all raw milestones, actions, perturbation clocks and final support windows.
Twenty-six focused tests and collision checks pass. Runtime is 152.994 seconds
inside the unchanged 300-second envelope.
Evidence: `artifacts/contact_validation_probe_20261004T215921117225Z/verification.json`
and `edge_support_review.json` beside it.

Next inspect terminal body-control authority using these captured edge-state
observations and original collision/terrain geometry. The final correction
is norm-saturated at 16 pixels, yet body X is fixed and sign proxy inactive.
That does not prove a larger gain will help or reveal contact forces.
Determine whether a distinct legal plant-and-recenter terminal stroke is
mechanically justified before freezing a new local test. No gain/cap/sign/
threshold sweep, replay of the closed validation or successful-case-only
corpus. Preserve all nine cases and the failed gate.
