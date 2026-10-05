# Ordered stroke-feedback diagnostic

The separately named residual scaffold is now implemented and passes
exact zero-correction fidelity. See `RESIDUAL_CONTROLLER.md`. Its unchanged
hand-designed ledge holds are not learning progress. No model is trained.

`research/stroke_controller.py` is a non-learning experiment, not a validated
teacher. It uses the same hash-bound 600-row nominal prior as the phase
controller. Only legal raw 217-feature pre-action inputs enter the controller.
Private phase and call count reset with every episode. The default remains
`mode="stroke_feedback"`; the opt-in clock ablation is described separately.

## Original motor and proposed feedback

The subsequent saved joint audit confirms the original conditional transfer
sign, but does not measure a new body response. During the completed local
tip phase, hammer queries remain zero and the pot drops6.321821 pixels.
A single stationary nominal-query point is legally reachable from the failed
pose, but its approximate footprint has no overlap. It admits a separate
point/contact feasibility test only, not a plant, push or teacher. See
`TERMINAL_CONTROLLER.md` and
`artifacts/joint_authority_audit_20261005_v1/verification.json`.

The subsequent point-only probe times out after30 steps, physical error
2.071702>1, final hammer queryfalse. It records21 intermediate hammer
queries but no net pot lift or point/contact gate pass. Source progress
stays frozen, both backend pairs/prefix histories are exact. No push or
learning is admitted. Intermediate query hits are not a retrospective
completion, force measurement or permission to change the failed gate.
Evidence: `artifacts/point_contact_probe_20261005_v1/verification.json`.

The offline transition audit verifies that query flags aggregate attempted
collision tests, not endpoint overlap or the true blocked branch. The first
two query/low-travel posts still leave a10.667937-pixel goal error.
Original conditional transfer supports designing a separately gated
contact/pressure primitive, not changing the failed geometric criterion.
Any proposed pressure requires an equal-history actual-body response
contrast before recovery or teacher admission.
Evidence: `artifacts/contact_transition_audit_20261005_v1/verification.json`.

The separate contact/pressure implementation passes14 new/365 full tests,
but its matched one-step body-authority contrast fails. Both arms have
actual pot delta `(0,0)` and finishY32/gain11/no holds. Pressure moves
the hammer differently, not the pot; both final hammer queries are false.
No pressure-phase/recovery/teacher admission follows. Next inspect the
unobserved solver branch and direction, not a contact/gain/target retry.
Evidence: `artifacts/contact_pressure_probe_20261005_v1/verification.json`.

The offline branch audit rejects interpreter-only call counters: both
backends execute compiled direct procedure-table calls. A standalone,
opt-in compiled-thread counter design is admitted for diagnostic metadata
only, pending delegation tests and instrumented/uninstrumented fidelity.
It cannot become policy input or labels, and no actual branch/body authority
has yet been observed.
Evidence: `artifacts/branch_direction_audit_20261005_v1/verification.json`.

The opt-in compiled counter now passes16 synthetic tests and exact
instrumented/uninstrumented original-physics fidelity across12 rollouts.
Every archived legacy row, all backend/mode histories and per-tick counter
histories match. Counts remain diagnostic-only, outside raw217/controller
inputs. Per-tick branch attribution is next; body authority, recovery and
teacher/learning gates remain failed or unadmitted.
Evidence: `artifacts/procedure_counter_fidelity_20261005_v1/verification.json`.

Validated attribution now shows that all eight failed approach steps and
both matched contrast actions use the free-hammer path, not the specific
blocked-body transfer procedure. Query hits at steps7–8 therefore do not
certify that transfer. Nominal367 does use the blocked path and moves the
pot right/up, but from a different high body pose. Counts are path evidence,
not forces or a matched proof that this plant works from the failed pose.
Evidence: `artifacts/branch_attribution_audit_20261005_v1/verification.json`.

The selected earlier support event still uses the same failed upper point,
from a body nearly38 pixels higher. Its legal reach does not establish
support from the low failed pose; the copied-point hypothesis is rejected.
The next direction selected a separately named residual-learning scaffold around the
unchanged legal contact-feedback prior, with exact zero-actor baseline
fidelity and explicit clock/own-command context. Hand-designed baseline
holds must not be reported as learning. No training is admitted yet.
Evidence: `artifacts/lower_support_audit_20261005_v1/verification.json`.

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

## Offline terminal-authority audit

No new gameplay. Six captured traces, 3600 rows, compare the edge failure with
nominal and a central noisy success. Every final 120-tick body window has
query contact on all ticks and zero horizontal movement. Hammer query hits
are zero in all three cases. Only the edge case saturates its correction on
all 120 ticks. Its hammer wanders at X383.358..390.854, far to the right of the
supported body at X293.728, while the sign proxy remains inactive.
This is consistent with moving a free hammer, not established body authority.
Query counts alone do not prove the internal wall-test branch or contact force.

At the captured edge endpoint, body render offset is `(0,20)`. The current
pointer's approximate equilibrium hammer target is `(386.605,80.010)`.
Original body collider geometry extends 37.059 pixels below its position
at direction 90; it is not a circular 21-pixel collider. The hammer collider
is a 16x16 bitmap at resolution 2, roughly 8x8 stage pixels. This explains why
terrain near world Y65 can support a body whose center is at Y104.

Static alpha columns find surface points near X293.728 and X319.728 at Y65,
but no surface in the sampled band at X267.728. Thus the initial offline
left-side `(-26,-40)` plant suggestion is discarded before physical testing.
One mechanically chosen right-side plant pointer `(26,-56)` targets about
`(319.728,68)`, within original reach at distance 44.407. Eighteen of 81
approximate footprint samples hit alpha. This is **not** renderer-certified
hammer contact, nor a tested action. A subsequent pointer `(0,-56)` requests
leftward hammer motion; the original blocked branch can then move the body
right. The original controller gains/caps and failed validation remain fixed.

The bounded audit stays inside its immutable 180-second deadline. Separate
bounded verification checks original SVG/bitmap geometry, hashes and pause.
A failed Pillow attempt to open the body SVG is preserved; XML inspection
resolved it without installing a converter or changing assets.
Evidence: `artifacts/terminal_authority_audit_20261004T221822853423Z/verification.json`.

Next freeze a new ordinary-spawn legal-prefix renderer test, not a nine-case
validation retry: reproduce the existing 600-tick edge trace, then compare
unchanged terminal continuation with a fixed right-side plant. Allow at most
30 plant ticks. Compare one leftward push against identical plant-only
history, requiring equal pre-inputs, actual renderer query/travel evidence
and positive incremental body-X response on both backends. Do not extend the
plant cutoff, scan pointer targets, place state or admit labels if it fails.
Only demonstrated local planting/body authority can admit a separately
declared full recentering stage. No force, recovery, teacher or learning claim
from approximate alpha or a one-step response.

## Real renderer plant and matched push

The frozen local test first reproduces the nominal 600-tick playback hold.
Each terminal arm then reaches the same edge state through the unchanged
600-tick contact-controller/noise history from ordinary spawn. Noise seed
12100 continues through the terminal actions; it is not switched off.

Plant-only and plant-push share 30 identical `(26,-56)` plant ticks. At the
one contrast tick, plant-only keeps that target and plant-push uses `(0,-56)`.
Their raw pre-inputs and full prior histories match exactly. The comparator's
one hold tick is the declared contrast, not a planting-cutoff extension.

| Arm | Final body position | Final retained gain |
|---|---|---:|
| Unchanged continuation | `(293.728,104)` | 83 |
| Plant-only | `(304.741,104.381)` | 83.381 |
| Plant plus one push | `(309.941,104.565)` | 83.565 |

Planting produces renderer hammer query hits on 13 of the 30 ticks, with zero
hammer travel at the last common plant step. The matched push adds
`(+5.2,+0.183846)` body displacement relative to plant-only, with exactly zero
hammer displacement difference. Both resulting states remain alive in the
secondary region with body or hammer query contact. This passes the declared
local planting/body-authority gate, not a three-second body hold.

At the pushed endpoint, body velocity is `(3.745,1.051)` pixels/tick, above
the central hold speed limit. Both intervention arms' best central qualified
window is only 0.16667 seconds. No new central hold, death or summit occurred.
Reaching X310 for one step is not safe completed recentering.

Eight rollouts use 4986 controlled and 960 reset ticks, zero learning. All
four full backend pairs and every recorded 600-tick prefix agree exactly.
Independent review reconstructs all raw milestones, proposed/applied controls,
continued noise and matched local response. Twenty-six focused tests and
collision checks pass.
Evidence: `artifacts/terminal_plant_probe_20261004T223832761543Z/verification.json`.

Next freeze a separate release/settling diagnostic on this known edge case:
retain the original 600-tick prefix, 30 fixed plant ticks and one fixed push;
then resume the unchanged contact-sign controller for 90 ticks. Compare
unchanged continuation, plant-without-push and plant-plus-push through that
same total horizon. Require final 90-tick central position/speed/body-contact
support and exact fidelity before admitting a full conditional terminal
controller. No extra pushes, target/cutoff tuning, labels, old nine-case gate
rewrites or immediate teacher/learning promotion.

## Fixed release and settling comparison

The previous nominal and 631-tick plant/contrast histories reproduce exactly.
Only the newly declared 90-tick release continuation is added, with the same
controller, targets and ongoing noise. All terminal arms run 721 ticks.

| Arm | Final position | Central qualified window |
|---|---|---:|
| Unchanged continuation | `(293.728,104)` | 0 seconds |
| Plant without push, then release | `(303.229,104)` | 0.16667 seconds best |
| Plant plus one push, then release | `(314.428,104)` | 2.96667 seconds |

The pushed branch settles to zero final velocity inside the central region.
However, its first release tick (controlled tick 632) has speed 2.18276,
above the unchanged limit 2. All remaining 89 ticks qualify for region/speed;
the final 90-tick body-query fraction is 0.98889. The original three-second
held detector and declared final-support gate therefore remain false.
No extra tick, relaxed detector or retrospective pass.

Eight rollouts, 5526 control and 960 reset ticks, zero updates, deaths or
summits. All four full backend pairs and all eight old nominal/631-tick
prefixes are exact. Independent review reconstructs every raw milestone,
continued noise and proposed/applied control, and identifies the lone
nonqualified transition tick without new gameplay. Twenty-six focused tests
and collision checks pass.
Evidence: `artifacts/terminal_release_probe_20261004T225830472380Z/verification.json`
and `settling_boundary_review.json` beside it.

Full conditional-terminal design and corrective-data admission remain blocked.
Next propose a distinct settle-aware local diagnostic, not a one-tick retry:
keep the same prefix, plant and push; explicitly allow a bounded settling phase
under the unchanged controller, then measure 90 qualified hold ticks using
the original region, speed and body-contact contract. Predeclare a 30-tick
settling safety cap, independent hold clock and complete maximum work budget
before physics. Timeout or loss of qualification is a failure, not an excuse
to extend the window. The closed fixed-90 failure and old nine-case failure
remain immutable. This new protocol can at most admit conditional-controller
design, not labels, teacher validation, learned skill or summit promotion.

## Observed settling and independent hold

`research/settled_hold.py` implements the new diagnostic monitor separately
from the unchanged `MilestoneTracker`. It accepts only consecutive finite
30 Hz states. A bounded settling phase waits at most 30 ticks for central
position, speed at most 2 and a body query hit. That trigger sample is not
counted. The next 90 consecutive region/speed/alive ticks form the hold window,
with original body-contact fraction at least 0.8. Timeout, qualification loss
or inadequate contact fails permanently; no rearming or renewed caps.

The unchanged action/noise diagnostic reproduces all old states and controls
through the available old prefixes. No extra pushes, target changes or speed
relaxation. The pushed branch settles in two ticks, then measures 90 hold
ticks with 90 body-query hits. It finishes at `(314.428,104)`, gain 83,
zero velocity, and also passes the original three-second central milestone.
Its continuous run ends after 723 controlled ticks. Both unchanged and
plant-without-push branches time out after 30 settling ticks at X293.728 and
X303.229, respectively; their runs stop at tick 661 without retries.

Eight rollouts, 5290 control and 960 reset ticks, zero updates, deaths or
summits. All four full backend pairs and old prefix controls/physical states
are exact. Independent review reconstructs the full monitor state machine,
distinct trigger/measurement samples, original milestones and every actual
control/noise tick. All 323 Python tests and collision checks pass.
Evidence: `artifacts/settle_aware_probe_20261004T232031597236Z/verification.json`.

This passes only the local conditional-terminal-design gate. The old fixed
90-tick failure and original 8/9 central validation remain unchanged. No
teacher labels or learner training admitted.

Next implement one causal conditional wrapper around the fixed contact
controller. It may attempt the unchanged 30-plant/one-push/settle/hold sequence
once, after 600 decisions only when the raw input reports a supported, slow
left-edge landing in secondary X285..305 and Y100..112. It must ignore case
names, noise seeds and recorded trace indices. Already-central states must
stay on the original controller exactly. Use only raw input and private
resettable phase/clock, preserve all action caps and no-rearm failure rules.
Predeclare clock alignment and a bounded real-game wrapper smoke before any
fresh cohort. A separate whole-wrapper validation and data/learner contract
are still required; no automatic old-gate pass or paid scaling.

## Causal wrapper implemented

`TerminalController` now takes only actual raw pre/post inputs and a private
clock. One state-based checkpoint after 600 executed transitions chooses the
unchanged plant/push/settle/hold sequence or permanent bypass. The complete
known edge recovery reproduces exactly; nominal and an already-central noisy
case remain on the original controls. Six-rollout smoke passes, followed by
the separately frozen nine-case whole-wrapper development cohort: 9/9 final
central support versus 8/9 original, with eight full bypass histories exact.
Fresh fixed-rule validation then reaches 8/9 central versus 7/9 original,
failing the strict 9/9 gate: a new edge recovers, but noise13105 remains at
`(269.482,32)` before the terminal checkpoint. No learning or label admission.
See `TERMINAL_CONTROLLER.md` for alignment, evidence and the admitted offline
earlier-acquisition audit, not terminal-trigger widening or paid scaling.
The completed offline audit finds a lower queried/zero-travel hammer at the
tick300 stroke and no final body authority. It derives one legal next-prior
hammer-world target for a separately frozen equal-input one-step release
test. This target is not an admitted corrective label or demonstrated
recovery; the failed fresh gate remains fixed.
The one-step equal-input check now demonstrates actual hammer release and
reduced target error, with no meaningful incremental body lift. A separate
single-pulse follow-through test is admitted next, with unchanged feedback
and noise, no second release or automatic terminal macro. Labels and
learning remain blocked pending recovery and full causal validation.
The fixed751 single-pulse continuation fails both ledge holds, retaining11
in both arms. The tip stays free initially but timed later strokes move away
from the incomplete release goal. The next separate local test qualifies
actual hammer-target completion with a bounded observed phase, not release
alone or pulse-duration tuning. Body recovery and learning remain unproved.
The new bounded raw217 hammer-target phase now times out at30 steps with
physical error3.304582, failing its unchanged1-pixel completion rule.
338 Python tests and full reference/fast local histories pass. Next is an
offline tracking/disturbance audit, not tolerance relaxation, extra ticks
or teacher/learning admission.
The offline tracking audit now finds a useful but imperfect past-cursor
disturbance estimate, with no new game exposure. One unit past-error
subtraction is proposed for an equal-state cursor-response check. Original
gravity/contact behavior still prevents a simple linear solver claim;
cursor alignment would not prove hammer completion or body recovery.
The controlled cursor response now improves alignment but slightly worsens
tip target error, with unchanged body motion. Only an opt-in memory-aware
feedback implementation/smoke is admitted, using actually issued command
history and unchanged goal/tolerance/cap. No target-completion or learner
promotion follows from this cursor-only pass.
The opt-in issued-command feedback smoke now completes its local hammer
goal in26 steps/error.870482, with exact default preservation and344 tests.
The body remains atY32/noholds. Only a causal source-clock/observed-goal
wrapper design is admitted next; no teacher labels, acquisition or learning
claim follows from local tip completion.
The source-clock wrapper now preserves the nominal trajectory and correct
ordered handoff, but the known failed case still retains11/noholds. The tip
is aligned while the body is19.157607 pixels from its source-row pose.
351 tests and physical fidelity pass. Offline joint-body authority/terrain
analysis, not another wrapper/gain/phase retry, is admitted next.
