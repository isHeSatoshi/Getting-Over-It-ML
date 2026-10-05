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
