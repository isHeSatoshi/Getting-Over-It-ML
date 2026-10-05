# Causal terminal controller

`research/terminal_controller.py` wraps the unchanged contact-sign trajectory
prior. It is a hand-designed controller, not a trained model or admitted
corrective teacher.

## Contract

Only raw 217-feature float32 observations and private resettable clock/phase
enter the controller. It never receives a case name, reset/noise seed, recorded
trace row or privileged game state. Every `action(pre)` must be followed by
`observe(post)` for the actually applied one-tick transition. The next pre-input
must exactly equal that post-input. Evaluation code separately verifies the
one-physics-tick interface and applies any declared noise.

There is one arming checkpoint after 600 observed transitions, before the
601st decision. It requires slow body-supported left-edge input:
X285..305 (upper bound exclusive), Y100..112 and speed at most 2. Boundaries
are compared in the existing float32 observation encoding, so encoded X305
is not mistaken for a left-edge state by reconstruction round-off.
A skipped checkpoint never rearms.

If eligible, apply 30 fixed plant commands `(26,-56)`, one push `(0,-56)`,
then resume the original controller. The base controller advances its private
clock during all actions, including overridden plant/push commands. Start the
settling monitor only from the post-state of the first release action, not
from the push post-state. Preserve the 30-tick settling cap, next-90-tick hold,
original support rules and permanent failure/success completion. Maximum
751 decisions, one attempt, no extra pushes or renewed caps.

Already-central/unsupported/fast inputs bypass the macro and retain exact
original control. Monitor tick labels count executed controlled transitions,
not the game's additional reset-settling ticks.

## Implementation smoke

Six original-renderer rollouts, three known cases on reference and fast:

| Case | Wrapper behavior | Final body position |
|---|---|---|
| Nominal | Bypass, original controls | `(322.586,104)` |
| Noise12100 edge | One attempt, 2 settle + 90 hold ticks | `(314.428,104)` |
| Noise12101 central | Bypass, original controls | `(325.311,104)` |

All finish with central final support and gain 83, no deaths or summits.
The edge uses 723 actual controls and exactly reproduces the entire previously
validated primitive trajectory, not just its endpoint. Both bypass cases use
751 controls; no case identifier enters the policy. No recorded controls
override wrapper outputs.

4450 controlled and 720 reset ticks, zero learning. All three full backend
pairs, original 600-tick prefixes, action/observe chronology, raw milestone
traces and actual noise application independently verify. The full 330-test
suite and collision checks pass; the final encoded-boundary change also
passes 15 focused tests.
Evidence: `artifacts/terminal_wrapper_smoke_20261004T234047944352Z/verification.json`.

## Whole-wrapper development cohort

A separately frozen comparison now covers all nine previous development
cases, original contact controller versus unchanged wrapper, both backends.
Each arm has the same maximum 751-tick opportunity. The original runs to that
cap; the wrapper also stops on its permanent monitor success/failure. These
are not equal executed ticks or matched terminal times.

| Reference arm | Final central support | Final secondary support | Retained gain |
|---|---|---|---|
| Original contact controller | 8/9 | 9/9 | 83 each |
| Unchanged causal wrapper | 9/9 | 9/9 | 83 each |

The wrapper attempts recovery once, on the observed edge state, finishing at
`(314.428,104)` after 723 controls, 2 settling ticks and 90 independent hold
ticks. The other eight cases bypass it; their full 751-tick control, physics
and base metadata histories exactly equal the original. This preserves
successful landings but does not independently exercise eight recoveries.

36 rollouts, 26980 controlled plus 4320 reset ticks, 159.047487 owned seconds
within the immutable 300-second work cap. No updates, deaths or summits.
All 18 full backend pairs, 36 old 600-tick prefixes, six smoke histories and
all raw metric/action/observe/noise reconstructions independently pass.
41 focused Python tests and JS collision checks pass; no controller changed.
Evidence: `artifacts/terminal_wrapper_cohort_20261005_v1/verification.json`.

This passes the new development gate, not the earlier failed 600-tick gate
or the closed fixed-90-tick release gate. It admits only fresh fixed-wrapper
validation. No teacher, corpus, labels, training or learned-policy promotion.

## Fresh validation: gate fails

The unchanged controller was subsequently frozen on unused reset14001,
warm-ups `(±.75,-.125)` and noise13100..13105, with the same support criteria,
maximum horizon and stopping rules. Exact case/seed-field searches included
hidden and ignored JSON/JSONL before declaration.

| Reference arm | Final central support | Final secondary support | Retained gain |
|---|---|---|---|
| Original contact controller | 7/9 | 8/9 | Eight at 83, one at 11 |
| Unchanged causal wrapper | 8/9 | 8/9 | Eight at 83, one at 11 |

Noise13101 reaches a new edge state `(295.169,104)` and activates the single
attempt, finishing `(315.238,104)` after 724 controls, 3 settling ticks and
90 independent hold ticks. Eight other cases bypass with complete original
histories preserved. This supplies a second physically exercised recentering
example but does not establish a robust teacher.

Noise13105 never acquires either hold. Before decision601 it is already at
`(269.482,32)`, body query hit, base phase599. The wrapper correctly bypasses
this ineligible lower state and finishes at the same pose, gain11. Final
body contact and slow motion there are low terrain support, not ledge acquisition.
The failure is before terminal recovery; no earlier causal error is yet
identified. Widening the terminal trigger or changing the gate would hide it.

36 rollouts, 26982 controlled plus 4320 reset ticks, 161.207101 owned seconds,
no updates/deaths/summits. All 18 full backend pairs, 18 fresh 600-tick
original-versus-wrapper prefixes, four historical nominal traces and full
raw support/control/chronology reconstructions pass. 41 focused Python tests
and collision checks pass, no controller code changed.
Evidence: `artifacts/terminal_wrapper_fresh_20261005_v1/verification.json`
and `failure_boundary_review.json`. The auxiliary boundary inspection first
assumed a `phase` metadata key; inspection corrected it to `selected_phase`,
without changing the frozen review or rerunning physics.

The strict 9/9 gate fails. No data/learner contract, teacher labels, corpus or
paid training is admitted from these eight successes. Earlier gates stay
immutable. Next is a bounded offline acquisition/contact audit of saved
nominal, failednoise13105 and successfulnoise13104 histories, not a trigger,
gain, target or cutoff sweep. A new physically justified hypothesis needs
fresh declaration and validation before any clock/memory-aware learning.

## Acquisition audit and proposed local test

The frozen offline follow-up checks six saved trajectories, 4506 rows, no
new gameplay or learning. The failed run reaches X250 and Y65 but never
X285 or Y100. Its final X becomes invariant at tick500; its last hammer
query hit is tick482. All final120 body-query hits, zero hammer hits and
120 saturated corrections describe a low-terrain stall, not body authority.

At the predeclared tick300 snapshot the failed hammer is lower and queried
with zero travel, while the nominal hammer is free. The failed body falls as
the hammer stays fixed. These later states differ, so this is an observed
stroke/contact mismatch, not a controlled causal explanation of the failure.
All compared noise streams differ from their first applied action.

One mechanically derived release goal uses the next ordered raw prior row:
hammer-world `(186.932344,3.814357)`. Subtracting the actual failed pre-body
and the original fixed `(0,20)` render offset gives legal pointer
`(-84.057472,-54.507466)`, reach90.864866 within26..102. No target, gain or
clock scan was performed. The reference point is a goal, not a valid
corrective label at this different state. No release or body lift is proved.

All six raw histories, three backend copies and original motor/blocked-body
source excerpts independently verify. Evidence:
`artifacts/acquisition_audit_20261005_v1/verification.json` and
`local_authority_proposal.json`.

Next is a separately frozen one-step baseline-versus-derived-action check at
controlledtick300 after299 exact ordinary-start failed-prefix steps, with
continued noise and a nominal600 historical gate. Six rollouts, at most2400
controlled plus720 reset ticks/180workseconds. Equal actual pre-input and
full fidelity are mandatory. Post-target error below both common-pre and
baseline-post errors, plus query release or
positive hammer travel can admit only further local controller design,
not recovery, labels or training. No additional actions, targets or timings
may be searched after seeing the response.

## Equal-state local release passes

The separately frozen one-step contrast reproduces all299 prefix controls,
physical states and actual pre-inputs. One derived action at tick300 changes
hammer-query hit from true to false and travel from0 to4.474497 pixels.
Target error falls from14.708234 to11.145062, below both common-pre and
baseline-post errors. Incremental hammer motion is `(-4.049067,+1.904252)`;
body differences are only about `4e-13` pixels, not meaningful lift.

The declared local actuator gate passes. This controlled release does not
prove ledge recovery or explain the earlier failed acquisition causally.
The two contrast arms stop at300 with no ledge hold. Nominal600 support
remains exact. Six rollouts/2400 controlled+720 reset ticks, 30.928560 owned
seconds; all raw controls/metrics/clocks, three full backend pairs and source
prefix/baselines independently verify. 41 focused Python tests and collision
checks pass, no controller or metric changes. Evidence:
`artifacts/hammer_release_probe_20261005_v1/verification.json`.

Next is a distinct frozen follow-through diagnostic: original versus the
same single tick300 pulse, then resume unchanged contact feedback and noise
through751 ticks, with the nominal600 gate. Six rollouts/at most4204 controlled
plus720 reset ticks/180workseconds. Require original central held event and
final90 supported central ticks, exact old prefixes/baselines and fidelity.
Secondary support cannot replace that gate. No second release, terminal
macro, target, gain or cutoff search. Passing would only admit later causal
controller design, not teacher labels, corpus or learning. All earlier failed
gates stay immutable; body lift and recovery remain untested.

## Single-pulse follow-through fails

The separately declared continuation runs both arms to751 ticks with no
second pulse or terminal macro. Baseline finishes `(269.481845,32)` and
the pulse branch `(269.479241,32)`, both gain11 and no central or secondary
hold/final support. No deaths or summits. The strict recovery gate fails;
neither causal-controller design nor labels/learning is admitted.

The local tick300 release reproduces exactly. Saved post-pulse history has
fixed-goal error9.504054 at301,14.798242 at302 and27.598087 at305 while
timed base phases continue advancing. The tip stays query-free through305;
its first later query hit is352, so immediate replanting is not the observed
problem. This describes an incomplete target/handoff, not a complete causal
diagnosis of the earlier failure or a direct one-step body effect.

Six rollouts/4204 controlled+720 reset ticks,36.495458 owned seconds.
41 focused tests and JS checks, all raw metrics/actions/clocks, three full
backend pairs and every available historical prefix/baseline pass.
Evidence: `artifacts/hammer_followthrough_probe_20261005_v1/verification.json`
and `handoff_review.json`. All earlier closed gates stay unchanged.

Next is a distinct bounded observed hammer-target completion test, not a
pulse-length search: the same one fixed world goal and pointer formula,
updated from actual raw body input until post-action hammer error<=1 pixel,
with at most30 steps/one attempt. The tolerance comes from the existing
stationary-stroke criterion. Query release alone is not completion, and
tip completion would not establish body alignment or ledge acquisition.
No later prior strokes or resumed feedback in this local stage.

Declare nominal600 gate and baseline299+30 versus candidate299+at most30,
both backends: six rollouts/max2516 controlled+720 reset ticks/180workseconds.
Candidate early stopping and equal maximum horizon must be explicit.
Keep legal axes/reach, exact old prefixes/300response/baseline329 and full
fidelity. Only observed target completion can admit further causal phase
design; recovery, composition, full validation and learning remain separate.
No goal/tolerance/gain/cap scans, added macro or extension of the failed751
experiment.

## Observed hammer-target phase: timeout

`research/hammer_target.py` implements the separately declared raw217 phase.
Each legal action is followed by its actual post-input; the next pre-input
must match. The fixed world goal is unchanged, pointer updates from actual
body position, and base playback stays frozen. Query release is not target
completion. At most30 steps, tolerance1 pixel, no rearm or renewed cap.

Eight new tests, 49 focused and338 full Python tests plus collision checks
pass. The original controllers and milestone detector remain unchanged.

The frozen six-rollout local comparison times out at30 steps. Raw goal error
is3.304590, physical goal error3.304582, outside the original1-pixel gate.
The hammer moves, but this is not target completion. Candidate and baseline
finish near `(268.89,32)`, both gain11/no holds; no deaths or summits.
No phase-controller design, recovery, teacher labels or learning is admitted.
Do not increase the tolerance or append ticks after seeing this result.

2516 controlled+720 reset ticks,30.220299 owned seconds. All six raw
control/metric/clock/action-observe histories, three full backend pairs,
old nominal600/baseline329/candidate300 physical histories and initial
equal299-prefix/pre-input reconstruct exactly. Base phase298/calls299
remain frozen during the goal stage. Evidence:
`artifacts/hammer_target_probe_20261005_v1/verification.json`.

Next is an offline audit of tracking error, actual pointer versus commanded
actions, contact and original servo/reach behavior. Any disturbance-feedback
proposal must use past actual pointer and own command history, not evaluator
noise seeds or future noise. No goal, gain, tolerance or cap search, noise
suppression or retry of this failed test. Body alignment, acquisition and
full validation remain separate requirements.

## Offline tracking audit and causal pointer proposal

The saved six-trace/2516-row audit adds no game exposure. All30 target-stage
post hammer query flags are false. Computed pre-state motor requests and
slew changes remain below original caps; target reach is within26..102.
But the actual hammer increment differs from the naive0.4 pre-state model
by up to4.707578 pixels on query-free steps. Original Gravity runs before
the motor, so those flags and this model cannot certify a free linear solver
or attribute all error to noise.

Actual raw pointer matches telemetry within3.78418e-6 pixels. Cursor-minus-
command residual averages4.583581 pixels. An estimate using only the next
pre-input's previous actual pointer minus the previous own command has mean
current-residual error1.488157/max9.968753;22/30 errors are under.002.
It is useful when the disturbance persists and stale when it changes.
No seed, current post-state or future applied noise enters this predictor.

One proposed unit past-residual subtraction uses the first target action,
not a selected low-error/noise block. Its legal pointer is
`(-84.985389709,-55.165676117)`. All counterfactual command arithmetic is on
recorded inputs only, not a new trajectory, release or target-completion
result. The failed1-pixel/30-step gate remains unchanged.
Evidence: `artifacts/tracking_audit_20261005_v1/verification.json`,
`causal_cursor_feedback_proposal.json` and `proposal_verification.json`.

Next is a separately frozen equal-state one-step uncompensated-versus-
compensated cursor response check after299 ordinary prefix steps, with
unchanged noise and a nominal600 gate. Six rollouts/max2400 controlled+720
reset ticks/180workseconds. Require strictly lower actual cursor error
relative to the common desired pointer and full fidelity/legal controls.
Report hammer and body effects even if they worsen. A cursor-alignment pass
admits only later causal feedback implementation/smoke, not labels, target
completion, body recovery or training. No disturbance-oracle input, filter,
gain, goal, tolerance or cap scan.

## Causal cursor response: alignment improves, tip error worsens

The separately frozen equal-state one-step check improves actual cursor
error to the common desired pointer from1.137445 to.000704 pixels.
But hammer-target error slightly worsens,11.145062 to11.265577.
Both hammer queries are false, travel4.474497 versus4.715063, body
difference exactly zero. This passes only the cursor-alignment gate, not
hammer tracking, target completion, body recovery or teacher competence.

The estimator reads the previous actual raw pointer and previous own
command only. Same299 ordinary prefix, same current pre-input/noise, no
seed or future-noise access. Six rollouts/2400 controlled+720 reset ticks,
31.341925 owned seconds;49 focused tests and JS checks pass. Full raw
controls/metrics/clocks, three backend pairs and source histories verify.
Evidence: `artifacts/cursor_response_probe_20261005_v1/verification.json`.

Next is an opt-in memory-aware feedback implementation and bounded pipeline
smoke, preserving exact default target-phase behavior. Bootstrap once from
the actual preceding prefix command and its observed post-input. Each
subsequent estimate must subtract the command actually issued by this
controller, not the uncompensated desired pointer, from actual post-pointer.
Strict action/observe/pre-post linkage and bootstrap guards are required.

Keep the same goal, unit subtraction, offset,1-pixel completion,30-step cap,
legal controls and no-rearm rules. Freeze nominal600 plus default-versus-
feedback target-stage smokes after299 steps, both backends, at most2516
controlled+720 reset ticks/180workseconds. Default histories and the new
first-step cursor contrast must remain exact. Require actual raw and physical
tip completion, not merely smaller cursor error. No filters, gain scans,
noise changes, labels or learning; even local completion would need later
body acquisition, composition and fresh whole-controller validation.

## Opt-in issued-command feedback completes the local goal

The memory-aware mode now preserves the exact default contract and all
historical default actions/observe summaries. Bootstrap occurs once from
the previous executed command and actual post-input. Every later estimate
subtracts the controller's own issued command, not its uncompensated desired
pointer. Input copies, bootstrap, pre/post ordering, legal controls and
permanent failure are guarded.14 phase tests,55 focused and344 full Python
tests plus collision checks pass.

The frozen smoke reaches the same fixed goal in26 steps: raw error.870480,
physical error.870482, actual motion/no death. The default still times out
at30 with error3.304582. Candidate stops at controlled325, default329.
Both bodies remain near `(268.85,32)`, gain11/no ledge holds. Local hammer
completion is not body alignment, recovery or a learned policy.

2508 controlled+720 reset ticks,30.222317 owned seconds, six rollouts.
All raw metrics/actions/clocks/memory updates, three full backend pairs,
four unchanged full nominal/default histories and first300 candidate
physics match independently. Evidence:
`artifacts/cursor_feedback_smoke_20261005_v1/verification.json`.
All previous failed gates remain fixed; no labels or training is admitted.

Only causal phase-controller design is next. Proposed wrapper has one
raw lower-planted-hammer checkpoint after299 actual transitions, no case
or seed input; ineligible cases permanently retain original controls.
The first goal action overrides one ordinary source-phase299 proposal,
then source progress freezes until observed goal completion. Resume the
next ordered source-phase300, not the elapsed physical clock. Failed target
completion is terminal, no rearm or extra macro. All ignored proposals remain
diagnostic, not labels. This clock/goal composition is not implemented yet.

Freeze a four-rollout nominal/knownfailed reference+fast smoke, max3004
controls+480 reset ticks/180workseconds/751maxhorizon, after unit/parity
checks. Nominal bypass and existing prefix/goal physics must remain exact.
Require full final central support, not goal completion or secondary support,
before broader validation. Body recovery, composition, fresh whole-controller
validation and a memory-aware learning contract remain separate gates.
