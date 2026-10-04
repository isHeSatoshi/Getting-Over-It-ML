# Autoresearch: learn Getting Over It in the original game

## Authority and objective

The user delegated research, implementation, operations, and experiment
decisions, with no further decision questions, on 2026-10-04. Continue across
scheduled invocations until independently verified completion, interruption,
or a real access, safety, or spending blocker. CPU Upgrade is authorized;
CPU XL is also authorized **after** the current pilot completes, if measured
capacity or elapsed-time needs justify it. Larger hardware is not a remedy
for a failed control or exploration design.

This is a long-running research goal, not a claim that success is guaranteed.
The scheduled operator and remote worker are separate: the worker executes
bounded batches; the operator examines evidence and selects the next batch.

## Physical success, not reward optimization

Primary metric: **worst-seed reference full-climb completion fraction**, higher
is better, for the best variant with all declared training seeds completed.
At least three distinct training seeds are required. Record first-ledge holds,
retained altitude, deaths, real game ticks, sample/update counts, wall time,
resource use, and compute cost independently.

A candidate requires nominal full completion in every training seed and
at least 80% completion in the nine declared reference cases per seed
(at least 8/9). Final success additionally requires:

- Independent held-out legal warm-ups/action-noise streams, at least 20 cases
  per seed, with at least 80% completion and a nominal completion for every
  seed. These cases must be declared before evaluating the chosen checkpoint.
- Fast/reference agreement covering its learned upper-route contact sequence.
- The original summit condition, body world Y >16000, on a continuous legal
  trajectory from the ordinary starting terrain. No placement, altered gravity,
  or fabricated collision geometry may count as learning evidence.
- A saved model, matching frozen normalizer, dependency/source/asset
  fingerprints, legal action trace, and replayable reference completion.

Structured perturbations are not IID physical worlds. Do not make binomial
confidence claims from their success fractions. MAD experiment comparisons
are advisory, not a substitute for independent training-seed replication.
`tools/research_goal_metrics.py` deliberately never declares the final goal
verified from standard campaign aggregation alone.

## Current remote state: admitted timing study running

- Configured session: **`timing-20261004-v1`**, mode **`timing_study`**.
- Private Space revision: **`362327f3281811b924089251aa67438fe64dc31e`**.
- Pinned secret-free operator context dataset commit:
  **`80884fcb942397b783c9562b2cf3b987879a21a8`**.
  Historical preflight context: `1df89ec0fe48a579c234fed9e4a2e26085279811`.
- CPU Upgrade, one replica, paid-default never-sleep (`sleep_time=None`).
- Reservation start: `1791088706.4052017`; immutable deadline:
  **2026-10-04 20:38:26 UTC**, epoch **`1791146306.4052017`**.
- Fresh maximum reservation **$0.48** at published $0.03/hour, verified
  2026-10-04. Closed v1/v2 elapsed estimates plus this reservation total
  **$0.672547**, below the unchanged $10 ceiling; this is not the actual bill.
- Explicit restart requested at `1791088979.409153` after source/context/
  variables were verified while PAUSED; it returned BUILDING. The next bounded
  monitor read returned APP_STARTING with durable phase `timing_admitted`.
- Pinned first-state review at dataset commit
  `bcdd369f039cb3cdfaf0fa654e378d209e423f9c` verifies exact source/game/asset
  hashes, start/deadline, configured context and runtime policy, with no error.
  Evidence: `artifacts/timing_deployment_20261004T044058033509Z/`.

**Timing preflight passed all eight checks and automatically paused.**
Pinned review at dataset commit `471eadaf676a498b52cabb5962312e3da94e378b`
validates exact source/game/assets, 17 raw-physics and six reactive timing
fidelity cases with zero measured errors, both matched smoke contracts,
effective 8 CPUs/32 GB cgroup allocation and never-sleep/one replica.
Terrain benchmark is about 266 decisions/s excluding optimization; summed
worker+reference peak RSS is about 6.08 GiB, not exclusive physical memory.
Independent PAUSED verification epoch: `1791089935.6895523`.
Evidence: `artifacts/timing_preflight_review_20261004T045845231549Z/`.

After reviewing that evidence while PAUSED, the operator published the exact
durable passed-preflight fields in the new pinned context, validated admission,
and changed **only `RL_CONTEXT_REVISION` and `RL_MODE`**. An intentional
`timing_study` restart at `1791090090.08562` returned BUILDING. Source, hardware,
session/start/deadline and $0.48 reservation are unchanged. No checkpoint resume,
extra replica, widened pilot gate or CPU XL scaling occurred.
The subsequent bounded monitor read returned **RUNNING**, durable phase
`timing_dispatch`, with no error. At dataset commit
`7a9a6cdb066dd30bc93da01a7228b7ce4aea38e6`, the operator verifies the exact
six-run campaign, admitted source/context/deadline and persisted
`claimed_no_resume` execution claim. Evidence:
`artifacts/timing_preflight_review_20261004T045845231549Z/study_kickoff/`.
No completed learner outcome or learning-progress snapshot was available in
that kickoff commit. Its then-false training-start metadata was not a runtime
monitor; the later active-run audit below corrects it from actual telemetry.
Inspect durable status/trace rather than assuming bookkeeping indicates
whether training is active.

The admitted study has six sequential runs: seeds 3,4,5, each repeat 1 then 4.
Each arm has nominal 393,216 controlled ticks and 3,840 planned policy optimizer
calls; decisions/gradient sample presentations/FLOPs are not equal. Both metrics
and all nine physical-time perturbation cases remain frozen. No learned outcome
is available at this kickoff, and no improvement/completion is claimed.
Do not upload, restart, resize, change variables/secrets or queue while it runs.
Next scheduled priority: inspect one pinned durable snapshot of current status,
claim/manifest/progress and any complete results with the timing checker.
Do not blindly resume interrupted work. At terminal failure/completion/deadline
verify durable artifacts and PAUSED; pause only this owned Space if necessary.

### First active run contract/accounting audit

At the 2026-10-04 05:17 UTC check the study remains RUNNING on the unchanged
source/context/deadline, phase `ppo_absolute_repeat_1_seed_3`. A pinned audit
at dataset commit `0520df2b4c6ab9e04f83e9fb71769900c23c61e3` validates its
remote admission, exact campaign/source/assets, default raw settled reward,
one-tick gamma `0.9998074776513175`, physical-time GAE `0.9872585449014338`,
rollout 8,192/minibatch 1,024/10 epochs and declared nine-case reference horizon.
All 437 complete sampled JSONL rows have the expected 400-decision cadence,
controlled ticks equal transitions, and monotonic whole 120-tick reset counts.
The last durable sample is transition **174,800**, controlled ticks **174,800**,
reset-settling ticks **2,040** (17 resets). Four stable checkpoint/normalizer
pairs through 160,000 transitions have immutable Hub metadata/nonzero sizes;
they were not downloaded/reloaded, so this is not policy portability evidence.

The sampled pose is approximately `(150.46,26.74)`, retaining 5.74 units, with
both central/secondary hold flags false in that current episode. Training
telemetry/previous peaks are not competence. No final training summary or
reference evaluation exists yet; the timing aggregator correctly reports all
six runs incomplete, no arm comparison or final-goal verification.
Evidence: `artifacts/timing_active_audit_20261004T051847531397Z/`.
The cost ledger's training-start metadata is now corrected from this actual
trace; reservation/start/deadline/source and financial caps are unchanged.
Next scheduled priority is the first completed result with companions, or a
bounded progress/terminal-status check. Keep the live study unchanged.

### First complete timing result: repeat 1, training seed 3

At the 2026-10-04 05:37 UTC check the first one-tick run is complete and the
unchanged queue is actively training `ppo_absolute_repeat_4_seed_3`.
Pinned dataset `112cb595ce2f2f42895b1e01d0185577c964f7b8` passes the timing
aggregator for repeat-1 seed 3, with manifest/admission/source/reward/evaluation
and training-work contracts intact. It has **0/9 central v1 holds, 1/9 secondary
support holds, zero full completions and zero evaluation deaths**. Median
retained gain is **0**, equal to its untrained baseline median.

The isolated secondary hold is `action_noise_5`: first qualified at 5.83 game
seconds, final approximately `(302.12,104)`, retaining 83 units. Body-query
hits cover 1,753/1,800 controlled ticks, including all final four seconds.
It remains just outside the frozen central X minimum 305. This is a genuine
declared-case support outcome under recorded reference metrics, not
nominal/robust skill, held-out success or portable saved-policy reproduction.
Nominal remains near `(1.01,21)`; most other cases stay near spawn/low terrain.
Neither the pilot gates nor metric definitions are changed.

Training reports **393,216 actual controlled ticks**, **4,440 reset ticks**
(37 resets), zero shortened terminal decisions, **3,840 actual policy calls**
versus the separately labelled 480 internal counter, and 1,453.60 learning
wall seconds. Model/normalizer companions are durable with nonzero immutable
Hub metadata; they were not downloaded/reloaded for this review.
All before/after reference cases consume 1,800 controlled ticks each and have
separately counted initial/automatic reset work.

The one-tick evaluation JSON is 81,189,517 bytes because it records four times
as many decisions as repeat 4. An initial operator-only 32 MiB size gate refused
it; verified immutable metadata permits a bounded 128 MiB retry, which passes
the full trace checker. This was an audit limit, not a learner failure, and
did not change the worker/source/settings. Use bounded per-file size metadata
before future timing-result downloads, rather than assuming pilot file sizes.
Evidence: `artifacts/timing_first_result_verified_20261004T054007933164Z/`.

Only one of six runs is complete. Do not rank timing arms, scale, promote or
infer a three-seed effect from it. Finish the same six-run study under its
unchanged deadline/cost cap; next scheduled priority is the paired four-tick
result or a bounded terminal/progress check.

### First matched timing seed pair validated

At the 2026-10-04 05:57 UTC check both training-seed-3 arms are complete;
`ppo_absolute_repeat_1_seed_4` is now actively training in the unchanged queue.
Dataset commit `b0865f09d77e33efe5cc3d7b660a9cb40b539517` validates both
complete run contracts, common dependencies/admission/source and durable
model/normalizer metadata. Three-seed cohorts remain incomplete, so the
aggregator deliberately returns no worst-seed timing-arm comparison.

Repeat-1 seed 3 retains its **0/9 central, 1/9 secondary holds**, median retained
0. Repeat-4 seed 3 has **0/9 central and 0/9 secondary holds**, median retained
**27.77**, nominal approximately `(271.29,51.95)` with retained 30.95.
Both untrained medians were 0; both trained arms have zero reference full
completions and zero evaluation deaths in the nine 60-second cases.
This is a descriptive single-seed tradeoff, not an established timing effect,
robustness claim, promotion or reason to scale.

Repeat-4 training has 98,304 decisions, **393,167 actual controlled ticks**
versus nominal 393,216, **6,960 reset ticks** (58 resets) and 24 terminal short
decisions. Repeat 1 has 393,216 decisions/controlled ticks, 4,440 reset ticks
and no shortened decisions. Each performs **3,840 policy optimizer calls**;
learning wall time is **1,453.60 /690.37 seconds** for repeats 1/4. Thus actual
controlled exposure differs by 49 ticks, reset exposure also differs, and
equal calls are not equal computation or gradient sample presentations.
Keep these differences explicit rather than labelling the arms equal-cost.

Repeat-4 `hammer_right` finishes at approximately `(281.47,100.50)`, retaining
79.50. Its last four seconds have unchanged decision-boundary coordinates
and 120/120 body-query hits, but it is outside the frozen secondary X minimum
285. This is an **outside-detector contact/pose candidate**, not independently
calibrated platform support. Do not call it "no physical support" solely from
the detector, and do not widen the metric after seeing it. Any future physical
calibration/replay must be separate, labelled post-hoc and leave the study
contracts unchanged.

Evidence: `artifacts/timing_seed3_pair_20261004T055834361889Z/`.
Next scheduled priority: complete seed-4 results or bounded status/progress,
then seed 5; keep source, queue, variables, cap and deadline unchanged.

### Outside-detector recorded-action replay, post-hoc only

At the 2026-10-04 06:17 UTC snapshot, seed-4 repeat-1 transition collection
is durable through 393,200 but no complete reference result is available yet.
The image/source/context/deadline are still unchanged and RUNNING. Rather than
poll or alter it, a bounded local diagnostic replays the recorded seed-3
repeat-4 `hammer_right` case from an ordinary reset, without policy inference,
training, privileged placement or new metric definitions.

All **1,800 controlled ticks** reproduce the remote body positions with
**zero** measured decision-boundary error. The independent local original
reference and fast traces have **zero** measured error in all tested per-tick
numeric/discrete telemetry. Final pose is `(281.47135,100.50353)`, retained
79.50 units. For the final four seconds, X/Y are unchanged on every tick,
body-query hits cover 120/120 ticks and physical speed is zero.
The headed original-renderer capture shows the pot at the raised Scratch
block's left lip with the hammer planted on lower terrain, consistent with
the observed contact/pose. No contact-force telemetry is claimed.

Both frozen central and secondary detectors still return false because this
pose is outside their X regions. Preserve that result exactly. The replay
establishes a real stationary contact sequence missed by these region bounds,
not cross-host closed-loop policy portability, general/held-out climbing skill,
full completion, or permission to retroactively widen a success metric.
Any future descriptor extension must be separately calibrated/predeclared;
do not infer "four-tick control cannot support the platform" from this miss.
Evidence: `artifacts/outside_detector_replay_20261004T061945777984Z/`,
including the original-renderer final capture and full legal action/trace JSON.
This is a post-hoc diagnostic of an already selected case, not a new learner
experiment. The active remote six-run batch and financial reservation remain
untouched. Next scheduled priority: seed-4 complete reference results, then
seed 5, or a genuine terminal/deadline check.

### Second matched timing seed pair validated

At the 2026-10-04 06:38 UTC check, the actual Space is RUNNING in
`timing_study`, phase `ppo_absolute_repeat_1_seed_5`, with unchanged
source/context/session/deadline, one never-sleep CPU Upgrade replica and no
durable error. Dataset commit `d939596698dc137221c4a9fa8faba5f510a06b22`
passes all four completed timing run contracts, including both seed-4 arms.
All game/assets/research-source hashes match the declared campaign. Final
model/normalizer companions have nonzero immutable Hub metadata; they were
not downloaded/reloaded, so this is not saved-policy portability evidence.

For seed 4, both repeats have **0/9 central and 0/9 secondary holds**, no full
completions and no deaths in the nine final 60-second reference cases.
Repeat 1 has median retained gain **23.57**, nominal `(646.96,52.59)` retaining
31.59; repeat 4 has median retained **-30**, nominal `(821.47,-9)` retaining
-30. Both untrained baseline medians were 0. The one-tick endpoint gain is
better for this seed, whereas seed 3's endpoint median favors repeat 4.
These two pairs do not establish a replicated timing effect, robust platform
retention, promotion or scaling eligibility.

Repeat-1 seed 4 records **393,216 controlled ticks**, **4,320 reset ticks**
(36 resets), no terminal-short decisions and **1,399.51 learning seconds**.
Repeat 4 records **393,196 controlled ticks**, **5,640 reset ticks** (47 resets),
12 terminal-short decisions and **676.22 learning seconds**. Both record
**3,840 actual policy optimizer calls**, separate from the internal counter
480. Actual controlled exposure differs by 20 ticks; reset work and decision/
gradient sample presentations also differ. Equal planned ticks/calls must not
be described as equal actual exposure, computation or information.

Repeat-1 `hammer_left` ends at `(282.42,101.50)` retaining 80.50, with all final
120 body-query-hit ticks, outside secondary X minimum 285. Repeat-4
`action_noise_4` ends at `(1015.57,176.71)` retaining 155.71, also with 120/120
final body-query hits. These are post-hoc contact/pose observations, not
independently calibrated landings or support-force measurements; neither
satisfies the frozen first-platform descriptors or constitutes full climbing.
Preserve them without widening active metrics or treating high endpoints as
policy success.

Across the four validated runs, **0/36 final reference cases complete the
game**, and none dies within its declared horizon. Both three-seed cohorts
remain incomplete, with no worst-seed arm comparison returned by the checker.
Evidence: `artifacts/timing_seed4_pair_20261004T063847993651Z/`, including
pinned companions, complete JSONs, summary and actual runtime/variable review.
Only evidence metadata in the local ledger changes; the reservation, source,
queue, context and immutable deadline stay untouched. Next scheduled priority:
the complete seed-5 arms or a bounded terminal/deadline verification, then
full-cohort analysis and verified automatic PAUSED before any new experiment.

### Legal expert demonstration prerequisite, no learning

At the 2026-10-04 06:57 UTC monitor snapshot, the actual timing session/source/
mode/context/deadline and one never-sleep CPU Upgrade replica remain unchanged
and RUNNING. Dataset `02c1e44b5b7088ed8e6d477e7919fc692a9f2e4a` still has
four completed evaluations. Seed-5 repeat-1 training telemetry reaches 360,400
controlled ticks with 4,080 reset ticks and both ledge flags latched in that
episode near `(322.82,103.78)`. This stochastic training episode is not a
complete frozen-policy reference result or a reason to promote the study.

Instead of polling or altering the batch, a bounded local prerequisite checks
the known legal first-ledge expert for possible future imitation. Eleven
ordinary-start reference/fast cases use 600 ticks each: original float64
targets, float32-normalized targets, and the nine already declared physical-
time warm-up/noise streams with float32 targets. Warm-up replaces the first
12 ticks, prediction remains indexed by controlled tick, and noise is held
for four ticks. No placement, policy inference, optimizer or learning occurs.
The diagnostic plan is saved before the replays; total controlled work is
13,200 ticks across both backends, plus separate reset settling.

Raw and float32 nominal trajectories both finish at `(322.58589,104)`,
retaining 83 units and passing both frozen ledge descriptors. Maximum action
quantization is approximately **0.00000381 pointer pixel**. Of the nine
20-second perturbed expert cases, **8/9 pass both central and secondary
detectors**, retaining 83 at their endpoints. Noise stream 4 fails both,
ends near `(246.91,83.83)` retaining **62.83**, never qualifies a central hold,
and has zero body-query hits over its final four seconds. All eleven tested
reference/fast traces have **zero measured per-tick error** and no full
completions or deaths.

An additional verifier incorrectly expected raw/float32 inputs to produce an
identical entire trajectory. It fails at tick index 40 with a 0.0002 body-Y
difference. Direct comparison finds maximum body-Y difference 0.00027,
body-X difference 0, rounded pointer-Y difference 0.001 and no tested
discrete-state mismatch. Correct interpretation: the same final landing/hold
survives this conversion, not bitwise intermediate-state identity. This
operator assertion failure is preserved in `validation.json`; it is not a
reference/fast fidelity failure.

These are open-loop **demonstration diagnostics**, not learned-policy,
independent held-out, three-seed robustness, full 60-second study evaluations
or final-game evidence. The selected historical expert and familiar noise
streams are not new IID trials. Keep active metrics and the primary learned
completion metric unchanged. The eight short legal landings make this expert
a plausible demonstration source, while the miss motivates reactive recovery/
observation-action data rather than assuming a memorized time sequence is
sufficient.

Evidence: `artifacts/expert_robustness_probe_20261004T070002812275Z/`.
Next priority remains completed seed-5 outcomes and verified terminal PAUSED.
Conditional future hypothesis: collect provenance-bound ordinary-start
observation/action demonstrations, check identical or nearby observation
states for conflicting time-indexed targets, then separately predeclare an
imitation-plus-recovery/RL comparison. No such training, new reservation,
deployment, source change or paid batch is launched by this diagnostic.

### Demonstration-assisted learning foundation implemented locally

The user explicitly requested implementation after the literature review.
`research.demonstrations` now collects **pre-action** raw 217-feature
observations and actual legal float32 targets from ordinary spawn. It uses
training reset 6001/noise streams 9100..9105, separate from standard evaluation
1001/8100..8105. The same original physics, reward/history observations,
one-tick absolute interface and both frozen metrics are preserved.
Bounded NPZ/JSON persistence verifies hashes, shapes, finite/legal values,
non-pickled data, game/environment provenance and physical eligibility.
Failed expert trajectories stay in the data with false training eligibility.

Nine 600-tick expert collection cases produce **5,400 physical rows**; six
pass the frozen central detector. **3,576 rows** are BC-eligible after removing
forced 12-tick left/right warm-up labels. Teaching opposing externally imposed
warm-ups at the same spawn caused an exact-state target conflict of about
1.0035; those intervention labels are not policy targets. After exclusion, one
exact-state conflict remains with target range about 0.0281, attributable to
the varied demonstrated actions. Near-state ambiguity and off-trajectory
corrective expertise remain untested. Do not call this time-indexed teacher
a DAgger oracle.

A first nominal reference comparison passes observation/action equality but
fails direct metadata equality because Python tuples become JSON lists.
Descriptors are now canonically serialized, and a new corpus is collected
without overwriting the first artifacts. The corrected **600-tick nominal
reference/fast raw pre-action observations, actions and outcome info match
exactly**. This does not verify all training streams or an upper route.
Corpus: `artifacts/demonstrations_20261004T072714652488Z/`.
Parity: `artifacts/demo_collection_parity_20261004T073039320276Z/`.

`research.behavior_cloning` implements actor-only PPO initialization using a
separate optimizer. It fits observation RMS on eligible demo data, freezes it,
and leaves value parameters, action log-std, fresh PPO optimizer state and RL
transition counts unchanged. Full cloning is deliberately **not admitted**
through this local smoke CLI. An eight-update/64-sample pipeline smoke lowers
supervised mean-square action error **0.255668 -> 0.145106**, but its short
nominal reference trajectory remains at spawn, with no hold/full completion.
This is working initialization machinery, not acquired climbing skill.

Saved model weights and frozen normalizer statistics match a repeated seeded
warm start exactly. A saved-model 128-tick reference/fast closed-loop check
has zero measured action/observation/reward/telemetry error and no success.
Smoke: `artifacts/cloning_smoke_20261004T073212387553Z/`.
Verification: `artifacts/cloning_pipeline_verification_20261004T073750651481Z/`.
All **187 Python tests plus JS collision tests pass**, including refusal to
silently extend a cloning smoke by repeatedly warming the same learner.

`research.imitation_study` records a **non-executing proposal** for fresh
seeds 6/7/8: scratch PPO, BC-only and BC-then-PPO, with common frozen demo RMS,
unchanged observations/reward/actions, central/secondary reference cases and
separate BC/RL sample and optimizer work. It is not equal total compute.
Plan: `artifacts/imitation_study_20261004T074252246079Z/plan.json`.
No new reservation, paid training, source upload, worker/queue change or
deployment occurred. The full clone/recovery/RL trainer, complete-study
checker and bounded worker admission still need integration and tests; the
current full-cloning guard must stay until those exist. Next bounded priority:
finish timing closure, then implement that admission and a genuine remote
first-skill comparison, not another viewer feature or unrestricted desktop
training. Preserve the $10 ceiling and require a fresh preflight/session/cap.

### Promising fine-control seed 5 and requested visible replay

Pinned dataset `0c07c5cbce7ae847715b815c044e668df363eff5` independently passes
the complete repeat-1 seed-5 manifest/training/reference contract. Its final
nine cases have **2/9 central and 5/9 secondary holds**, median retained gain
**82**, zero full completions and zero evaluation deaths. Nominal ends at
`(320.52873,104)`, retaining 83 and passing both hold metrics; hammer-left
also passes central at approximately `(333.28,103)`. This is the first
validated nominal learned hold in this timing study, but not robust all-seed
or full-game competence. Fine central counts across seeds 3/4/5 are 0/0/2,
secondary 1/0/5, so this configuration still lacks all-seed retention.

Training reports 393,216 controlled ticks, 4,440 reset ticks/37 resets,
zero short decisions, 3,840 actual policy calls and 1,450.23 learning seconds.
Final binary companions have immutable nonzero metadata; they were not
downloaded/reloaded. The full coarse cohort/terminal pause is not reviewed
in this implementation chunk. The latest actual-variable check at 07:19 UTC
had unchanged source/context/session/deadline, RUNNING, one never-sleep CPU
Upgrade replica. Read actual status again next invocation, not this historical
phase, before acting.
Evidence: `artifacts/visible_learned_run_20261004T072937674870Z/run_review.json`.

The user asked to watch the most promising run. `research.visible_replay`
checks all nine run contracts plus actual game/critical-source hashes, then
plays recorded nominal targets through the original renderer, with per-tick
body-position checks. It is labelled **recorded actions, not live training,
local inference or full completion**, runs near 30 Hz, pauses at the final
pose and repeats for at most 30 minutes.

Detached-process viewer attempts fail first from a Git dependency and then
ChromeDriver initialization; the native detached window does not persist
across command cleanup here. The browser-owned implementation uses Factory's
persistent Chrome Browser pane instead, not a saved user browser profile.
It is observed progressing through tick 587 without recorded-position error;
the user subsequently confirms seeing it sit on the ledge. Some later pane
inspection calls return an about:blank evaluation context despite the tab
listing the game. Do not claim that proves a replay failure or keep navigating
the user's requested view. They have been told that the policy stalls on this
ledge and cannot improve while replaying. Do not spend more research time on
viewer polish, do not portray this hold as the summit, and do not cancel the
operator merely because a run/study finishes.

### Completed historical pilot, immutable evidence

- Private Space: `isHeSatoshi/rl-over-it-poc-20261004`.
- Private artifacts: `isHeSatoshi/rl-over-it-research-artifacts`.
- Completed dataset session: `poc-20261004-v2`.
- Historical deployed revision: `34c35854133294f97fef741479641f571371b8a3`.
- Interrupted historical session: `poc-20261004-v1`, revision
  `b3bf197090f1fb5219e5cce70a0dbfcca6576ce1`.
- Tier: CPU Upgrade, one replica, sequential nine-run pilot.
- Persisted deadline: **2026-10-04 12:21:08 UTC**, epoch `1791116468.8050392`.
- PPO/absolute, SAC/absolute, SAC/velocity, seeds 0/1/2, 98,304 transitions
  each. Four-tick actions, settled reward, terrain, raw rewards, common
  physical-time discount, reference evaluation.

**The full v2 pilot completed and automatically paused on 2026-10-04.**
A pinned review of dataset commit
`7c29b01d5cae53606f252511337a70b07a09699c` validates all nine runs under
their recorded source/game/reward/evaluation contracts. The original source
revision was retained at closing; it is now historical. Never mix these
completed outputs with the separately versioned timing diagnostic.
All 81 final reference cases have zero full-climb completions and zero deaths
within their 60-second horizons. PPO v1 holds are 0/9,0/9,1/9; both SAC
cohorts are 0/9,0/9,0/9. No variant passes follow-up or scale admission.
Worst-seed reference completion is 0; neither candidate nor final goal passes.
All nine final models/normalizers and all six SAC replay buffers are durable
at that immutable dataset revision, with nonzero sizes and Hub object metadata.
This closing review did not download/reload those large binary companions;
do not mistake durable presence for cross-host policy-transfer verification.
Evidence: `artifacts/v2_complete_review_20261004T024603257492Z/`.

The operator independently verified PAUSED at epoch `1791081974.4473813`.
The ledger is closed at a conservative v2 compute estimate of $0.153724,
or $0.192547 across v1/v2, including elapsed pauses/build/preflight time.
These estimates are not the actual provider bill. That pilot is closed;
the distinct active timing reservation is described above. Keep the operator
running for useful bounded research work.
Do not restart the completed pilot or overwrite either artifact session.
The next priority is the predeclared timing diagnostic, not promotion or
blind sample/hardware scaling. Timing-aware trainer/GAE/horizon and actual
training/reset tick accounting now pass local tests and bounded smokes.
Secondary-detector integration and bounded local timing-specific reactive
fidelity now pass. A distinct non-executing run contract/aggregator now passes
local tests. A remote-only sequential executor/admission foundation now passes
local tests and is now wired into fresh timing worker modes and narrowly scoped
trainer admission. Local integration checks and smokes passed before the
distinct capped timing reservation/deployment described above. Review durable
passed timing preflight evidence plus PAUSED before any intentional study launch. Direct remote
timing CLI use without a parent-bound run grant remains refused.

Never modify, upload, restart, or resize an active future image. The replacement
includes complete-prefix snapshots for append-only logs/CSV/JSONL; binary
checkpoints still require stable-copy checks. The historical v1 image could
skip continuously appended files, so its stale logs are not a stalled-learner
proof.

The completed pilot's original gates remain unchanged. A separately labelled
new diagnostic is allowed under the delegated authority, but is **not**
promotion of this failed pilot.

### Provider interruption and fresh replacement

On the 2026-10-03 21:35 UTC check, v1 was **SLEEPING** under the provider's
one-hour idle timeout, despite active background training. The operator
verified and requested PAUSED, then confirmed PAUSED. Three complete PPO runs
remain durable; SAC/absolute seed 0 has only a 20k checkpoint and telemetry
through transition 21,500, no final evaluation, and no saved replay buffer.
Do not silently resume that checkpoint or merge partial SAC into cohort results.
Incident: `artifacts/provider_sleep_incident_20261003T213845836829Z/`.

The explicitly fresh replacement session is **`poc-20261004-v2`**, with a full
new nine-run matrix under one new source snapshot, unchanged scientific
settings, corrected optimizer accounting, and append-only artifact snapshots.
This is a recovery/rerun, not promotion or checkpoint resume. Never overwrite
v1's artifact prefix. Replacement budget is reserved in the cost ledger.
Its deadline remains **1791116468.8050392**, with `RL_DEADLINE_EPOCH` enforced
in addition to the ordinary per-batch cap.

While PAUSED, the operator called `set_space_sleep_time(-1)` and configured
the replacement session in `preflight` mode. HF represents the paid-tier
never-sleep default by **omitting gcTimeout**, so `sleep_time` is `None`,
not necessarily `-1`. The verified API returned PAUSED with no finite timeout.
The new worker rejects finite sleep time, wrong hardware, or extra replicas.
Preflight must pass and auto-pause before any intentional switch to pilot.
The initial v1 epoch/source in older loop text is historical: read this state
and the actual configured session rather than overwriting it with old values.
Replacement source is uploaded as Space commit
`34c35854133294f97fef741479641f571371b8a3` from the allowlisted bundle
`artifacts/hf_bundle_20261003T214507412596Z/`. Its explicitly fresh preflight
restart returned BUILDING. Local replacement validation passes **87 Python
tests plus JS tests**.
The active operator was replaced with updated session-aware instructions.
The replacement's remote preflight subsequently completed and auto-paused.
A pinned dataset review verifies all 87 tests, JS checks, 17 fidelity cases with
zero measured error, exact game/source fingerprints, effective 8 CPU /32 GB
quota, never-sleep policy, and the unchanged deadline.
Benchmark: about 247 terrain-enabled decisions/s without optimization;
worker plus reference peaked at about 6.07 GiB summed RSS.
Review: `artifacts/v2_preflight_review_20261003T215809890172Z/`.
After those checks, the operator intentionally changed only `RL_MODE` to
`pilot` while PAUSED and requested a fresh start. It returned BUILDING on the
same source revision. No checkpoint or prior run was resumed or mixed in.
The replacement's first completed PPO/absolute seed-0 run is contract-validated:
98,304 transitions, 0/9 v1 holds, no full completions, no deaths in the final
reference horizons, and median retained gain 24. It reports 3,840 actual policy
optimizer calls versus the separately labelled SB3 counter 480. Learning wall
time was 813.01 seconds. These physical outcomes agree with historical seed 0,
but the runs remain separately recorded under their own source snapshots.
Evidence: `artifacts/v2_run_review_20261003T222052247473Z/`.
Replacement seed 1 subsequently passes contract aggregation with 98,304
transitions and 3,840 optimizer calls: 0/9 holds, no full completions/deaths,
median retained gain 43.51. The cohort remains incomplete; no promotion.
Review: `artifacts/v2_two_run_review_20261003T224226570388Z/`.
The complete replacement PPO cohort subsequently validates at v1 hold counts
0/9, 0/9, 1/9, with no full completions or final-horizon deaths. It reproduces
the historical cohort's aggregate physical outcomes, without pooling sessions.
The first SAC/absolute run is actively training; no SAC effectiveness conclusion
is available yet. Review: `artifacts/v2_ppo_cohort_20261003T225813655321Z/`.
SAC/absolute seed 0 subsequently completes and passes contract aggregation:
98,304 transitions, 0/9 holds, no full completions/deaths, median retained
gain 0. Every final case remains at `(0,21)`. Its nominal predicted Y target
stays positive, approximately `[0.704,0.990]` normalized, and the hammer records
zero terrain-contact ticks while the body remains grounded for all 1,800 ticks.
This is a physically inactive controller outcome, not a control-bridge failure.
The exact cause of learning this behavior is not yet isolated; one seed does
not establish an algorithm-level conclusion.
It performs 88,304 actor, 88,304 critic, and 88,304 temperature optimizer calls
(264,912 total), with learning wall time 2,154.72 seconds, versus PPO seed 0's
3,840 combined-policy calls and 813.01 seconds at equal transitions.
Calls are different operations, not equivalent FLOPs. Both sample and wall-time
comparisons must remain explicit. A durable final SAC replay buffer is present;
only JSON metadata was downloaded for this review, not the large replay object.
Evidence: `artifacts/v2_first_sac_review_20261003T233847089245Z/`.
SAC/absolute seed 1 subsequently passes the same contracts with 98,304
transitions and 264,912 named optimizer calls, learning wall time 2,180.17
seconds, 0/9 holds, no full completions/deaths, and median retained gain 0.
Its nominal body remains near `(0,20.57)`, predicted Y is approximately
`[0.821,0.988]`, hammer contact is zero, and body contact covers all 1,800 ticks.
Across final cases the body stays at X=0 with Y approximately 20.57 or 21.
A final replay buffer is durable. This repeats the inactive/above-ground-hammer
outcome at a second training seed under this configuration and sample budget.
The three-seed cohort remains incomplete, but these failed seeds already
prevent its predeclared all-seed promotion gate; do not silently loosen it.
Evidence: `artifacts/v2_second_sac_review_20261004T001803114793Z/`.
The complete SAC/absolute cohort subsequently validates **0/9 holds in all
three seeds**, zero full completions/deaths, and median retained gain 0 for
each. Seed 2 repeats the grounded/no-hammer-contact outcome: nominal `(0,21)`,
predicted Y approximately `[0.273,0.987]`, zero hammer contact and 1,800 body
contact ticks. It records the same 264,912 named optimizer calls and 2,166.11
learning seconds. All three final replay buffers are durable.
This source/configuration/budget fails the predeclared gate and is not eligible
for broader-climb scaling. Do not generalize this to all SAC variants or game
solvability. The three velocity-action SAC runs remain in the unchanged queue.
Evidence: `artifacts/v2_absolute_cohorts_20261004T005803065949Z/`.
SAC/velocity seed 0 subsequently passes contract validation: 98,304 transitions,
264,912 named optimizer calls, 2,092.21 learning seconds, 0/9 holds and no full
completions/deaths, but median retained gain 6 rather than complete inactivity.
Its nominal case finishes near `(86.83,27)`, retaining 6 units, with 18 hammer
contact ticks and 1,776 body-contact ticks. Other cases retain roughly 0..8 units
on low terrain and reach X up to about 210. This is physical movement under
velocity control, not first-platform retention or robust climbing.
One seed remains insufficient for the parameterization comparison. Because
this seed fails the frozen all-seed gate, the variant cannot qualify for the
current follow-up even if later seeds improve; preserve their remaining runs.
Evidence: `artifacts/v2_first_velocity_review_20261004T013812716866Z/`.
SAC/velocity seed 1 subsequently validates at 98,304 transitions, 264,912 named
optimizer calls, 2,114.77 learning seconds, 0/9 holds and no full completions/
deaths, median retained gain **31.91**. Its nominal endpoint is approximately
`(255.16,130.67)`, retaining 109.67 units, but not a body-supported landing.
Over its last four game seconds, decision-boundary X varies 243.31..255.16
and Y 113.36..130.67, with 120 hammer-hit ticks and zero body-hit ticks.
This is a contact-rich lift/traversal trajectory, not settled platform support.
Two warm-up cases remain at spawn; other final cases retain roughly 29..40.47
units. A final replay buffer is present. The velocity cohort still has one
missing seed, and both completed seeds fail the fixed retention gate.
Evidence: `artifacts/v2_second_velocity_review_20261004T021802585667Z/`.
SAC/velocity seed 2 subsequently completes and validates: 98,304 transitions,
264,912 named optimizer calls, 2,087.04 learning seconds, 0/9 holds and zero
full completions/deaths. Median retained gain is **3.51**, with nominal endpoint
approximately `(141.49,24.51)`, 1,723 hammer-hit ticks and 1,085 body-hit ticks.
The complete velocity cohort fails the frozen gate. Its untrained versus
trained median retained gains are respectively 26.54->6, 22.71->31.91,
25.40->3.51 for seeds 0/1/2. Therefore even low-terrain endpoint movement
must not be presented as consistent improvement from learning.
The complete matrix is validated and PAUSED, not awaiting another run.
Evidence: `artifacts/v2_complete_review_20261004T024603257492Z/`.

## How to inspect and measure

On Windows, from the repository, using the existing authenticated HF CLI:

```powershell
& .\venv\Scripts\python.exe .\tools\hf_research_status.py
hf spaces info isHeSatoshi/rl-over-it-poc-20261004 --expand runtime --json
```

Download only bounded, trusted JSON artifacts needed for aggregation into a
new uniquely named local directory, pinned to one private dataset commit.
Required: campaign.json and each completed run's manifest.json,
training_summary.json, evaluation.json. Treat an upload that has evaluation
but not its required companions as incomplete, not an experiment failure.

```powershell
& .\venv\Scripts\python.exe -m tools.research_goal_metrics --directory D:\absolute\artifact_snapshot
```

Linux equivalent: `bash autoresearch.sh /absolute/artifact_snapshot`.
The script only reads/validates artifacts. It must never train on the desktop.
`bash autoresearch.checks.sh` runs correctness checks on a suitable Linux
environment; Windows equivalent is unittest discovery plus the JS test.

The current source is mostly uncommitted pre-existing work. The research branch
preserves it. Do not use broad checkout, reset, stash-drop, or git clean as
"experiment rollback." Use new artifact directories, isolated future source
snapshots/worktrees, or restore only known agent-created changes. Do not stage
unrelated existing work or alter Git identity.

## Bounded spending and failure handling

- Retain the current persisted 16-hour deadline; do not reset it.
- For future batches, use distinct session IDs and a persisted start/deadline.
  CPU Upgrade batches: at most 16 hours. CPU XL capacity benchmarks: at most
  30 minutes; initial XL training batches: at most four hours.
- Begin with one active run. Raise concurrency only after owned-process,
  optimizer, cgroup, memory, disk, and fidelity measurements justify it.
- Verify live pricing before changing tier. Previously quoted pricing was
  $0.03/hour CPU Upgrade and $1/hour CPU XL.
- Maintain a cumulative estimated paid-compute ledger. Initial operating
  ceiling is **$10 including the current pilot**. Do not silently renew this
  ceiling or assume HF credits are unlimited. At the ceiling, pause paid
  compute, preserve state, continue cost-free analysis, and report the blocker
  without asking another decision question.
- The ledger is `autoresearch.costs.json`. Reserve the planned maximum batch
  charge before launching; count elapsed time conservatively, including pauses,
  until a verified end is recorded. This estimate is not the actual HF bill.
- Pause the owned Space at batch completion, terminal failure, or deadline.
  Verify PAUSED and durable outputs. Never automatically resume a partially
  lost batch: recovery needs explicit source/checkpoint and replay-state
  integrity tests, or a separately labelled fresh experiment.
- Keep repos private. No public redistribution, GPU tiers, additional paid
  providers, real user browser sessions, unrelated processes, or account
  changes. Strip credentials from child processes and never log them.

## Hypothesis and expansion policy

For each future experiment, write its hypothesis, baseline, frozen settings,
sample and physical-time budget, seeds, evaluation cases, and stopping rule
before execution. Change one substantive factor where possible. Keep a
positive result only after full contract checks and independent replication.
Record failed experiments and why they failed; do not erase them.

1. If the current pilot passes its predeclared first-ledge gates, use its
   controlled broader-climb follow-up, not immediate large-scale training.
2. If it fails, prioritize **action timing/feedback**. An exact legal per-tick
   trajectory already reaches and holds the first ledge; resampling it to
   four-tick actions at phase zero fails. Other sampling phases can land and
   hold the same platform outside the narrow benchmark region. Test one-tick
   versus four-tick control with matched
   physical exposure, physical-time gamma, horizon, warm-up duration, and
   evaluation duration. Separately report decision and optimizer budgets.
3. If timing alone is insufficient, investigate exploration/skill acquisition:
   legal successful trajectories, imitation pretraining, outcome-conditioned
   replay, or structured curricula. Synthetic placement/calibration must stay
   separate from ordinary-start evaluation and be explicitly labelled.
4. Scale samples only for a physically improving, reproducible controller.
   Scale hardware only for a measured resource constraint or useful parallel
   throughput, not to hide a failed hypothesis.
5. Final completion verification uses frozen held-out cases, upper-route
   fidelity, legal ordinary-start trajectories, and saved-policy replay.

## What's been tried

- The legacy Node backend lacked renderer collisions, fixed body X, and
  confused controller memory with contact. Legacy learning claims are invalid.
- The original compiled game plus real renderer is causally validated.
  Fast exact-query caching matches reference on tested traces. Full upper-level
  fidelity is not yet established.
- Original controller offsets are player-relative, with eased/clamped reach.
  Body spawns at Y=21; real contact-based actions move and lift it.
- Legal bounded per-tick search holds the first ledge near `(322.59,104)`;
  four-tick resampling and the bounded four-tick search fail the hold.
- A matched 600-tick causal timing probe reproduces that per-tick success and
  all four held-action phases with **zero** fast/reference telemetry error.
  Phase 0 retains only 38.33 units. Phases 1/2 settle at approximately
  `(289.50,104)` / `(289.92,104)`, retain 83 units, and have body contact on
  every tick of the final four seconds. The original pilot's X `[305,335]`
  region rejects these genuine edge-supported platform landings.
  Keep the pilot contract frozen, but do not infer "four-tick control cannot
  climb" or "no platform support" from that narrow metric.
  A post-hoc **secondary diagnostic**, `first_platform_support_diagnostic_v2`,
  uses X `[285,345]`, the same Y/speed/three-second/body-contact requirements.
  It passes per-tick and coarse phases 1/2, not phases 0/3. It is neither a
  promotion gate nor learned-policy evidence. Declare/calibrate any new
  platform metric before a future learning experiment and retain v1 alongside.
  Evidence: `artifacts/timing_probe_20261003T211346899540Z/` and
  `artifacts/timing_support_review_20261003T211614229092Z/`.
- `climb-v2` reward is raw, potential-based, physically discounted, with observed
  settled-history state. Transient peaks and repeated contact are not success.
- Pilot PPO/absolute seed 0: 98,304 transitions, 0/9 reference ledge holds,
  0/9 full completions, median retained gain 24 versus baseline 0, no deaths
  in the nine 60-game-second final cases. This is movement, not climbing skill.
  Evidence: `artifacts/remote_pilot_review_20261003T204729761166Z/`.
- Pilot PPO/absolute seed 1 also completed 98,304 transitions with 0/9 ledge
  holds and 0/9 full completions, median retained gain 43.51, and no deaths
  within its final reference cases. Both runs pass contract aggregation.
  The three-seed cohort is still incomplete, so no variant-level selection
  is made. Latest pinned review:
  `artifacts/remote_goal_review_20261003T210724262386Z/`.
- The complete PPO cohort is now validated: v1 holds 0/9, 0/9, and 1/9 for
  seeds 0/1/2, with no full completions and no deaths in these final horizons.
  Seed 2's `action_noise_2` case holds by 5.33 game seconds, then stays near
  `(328.75,104)` through the 60-second horizon, retaining 83 units.
  This is the first learned-controller ledge hold, not robust success or
  promotion. Nominal finals are approximately `(277.30,51.38)`,
  `(280.26,64.50)`, and `(652.03,54)`. The PPO cohort is recorded as failing
  the robustness gate; finish both SAC cohorts before selecting the next batch.
  Evidence: `artifacts/remote_ppo_cohort_20261003T212305324947Z/`.
- The 20k checkpoint visibly controls the real hammer and moves to about
  `(109.28,79.70)` in a short nominal trace. It is brittle. An evaluation's
  post-reset screenshot must not be presented as its final policy pose.
- The historical v1 pilot's PPO `training_summary.gradient_updates` stores SB3
  `_n_updates`, an epoch count rather than minibatch optimizer steps.
  The correction, now deployed in v2, uses removable Torch
  post-step hooks and `optimizer-step-calls-v1` per-optimizer counters.
  It leaves tested PPO weights bitwise unchanged, supports checkpoint save/load
  during instrumentation, and removes hooks after success/failure.
  Actual 128-transition game smoke integrations report PPO 8 policy calls
  versus internal counter 4, and SAC 64 actor +64 critic +64 temperature calls
  versus internal counter 64. These are pipeline tests, not climbing evidence.
  Evidence: `artifacts/trial_20261003T212111941726Z/` and
  `artifacts/trial_20261003T212200168900Z/`.
  Optimizer-call counts are not equal FLOPs or equal compute across algorithms;
  keep wall time, configuration, physical exposure and hardware alongside.

## Continuity and termination

Read this file, `autoresearch.jsonl`, `autoresearch.ideas.md`, and latest durable
remote status before every scheduled research action. The old monitoring loop
must be replaced because it forbids all follow-ups and cancels after the pilot.
The new operator may continue with bounded diagnostic/follow-up batches after
the current worker is paused and outputs are validated.

Cancel the operator on user interruption or independently verified final
success. On access/funds/safety blockers, stop affected paid actions and state
the exact limitation; do not claim to work or spend invisibly. At context
limits, save the journal and experiment log so the next invocation resumes.
Never promise that unlimited compute or indefinite scheduling guarantees a
solution. Do not ask "should I continue?"

Goal setup checks pass 68 Python tests, the JS collision tests, both Bash
entrypoint syntax checks, and read-only metric extraction against the pinned
partial pilot snapshot. Windows' default WSL Bash is broken on this host;
Git Bash syntax validation succeeds. Use the venv Python directly on Windows.
The timing diagnostic subsequently passes all 75 Python tests plus JS checks.
Future-snapshot optimizer accounting subsequently passes all 81 Python tests,
JS checks, and bounded real-game PPO/SAC integration checks.
Recovery admission/deadline safeguards subsequently pass all 83 Python tests
plus JS checks. A first assertion expected literal sleep_time=-1; inspection
confirmed HF's paid-default None representation, and tests now cover both.

## Prepared next-snapshot shutdown hardening

The live v2 source remains unchanged. A **local-only** worker correction bounds
initial/final artifact flushing to 20 seconds and pauses even if upload fails
or hangs. It covers normal completion, expired budget at boot, interrupted
restart refusal, deadline watchdog, and fatal startup handling. This addresses
an unbounded final `sync()` after the live worker stops its watchdog. Periodic
snapshots and the external operator remain the current live safeguards.
Do not deploy it mid-pilot; apply it only in a future paused source snapshot
with fresh preflight. A timed-out flush may leave the last snapshot incomplete,
so verify durable models/evaluations/replay before any recovery or promotion.

The correction passes **90 Python tests plus JS checks**, including successful,
failed, and deliberately blocked upload fixtures proving pause still occurs.
No changes to learner, reward, physics, budget reservation, or live deployment.

## Learned-trajectory transfer verification

A local-only extension of `research.policy_fidelity` can replay any declared
standard perturbation with the same reset seed, warm-up actions, and action
noise stream as the standard evaluator. Tests preserve legacy fixture behavior
and check exact seeded-noise/warm-up semantics. All **93 Python tests plus JS
checks** pass. Do not deploy diagnostic changes into the running pilot.

Using the trusted historical PPO seed-2 final checkpoint and its frozen matching
normalizer, `action_noise_2` reproduces the v1 hold on both original reference
and fast backends for 96 decisions (12.8 game seconds). Predicted/applied actions,
normalized observations, rewards, physical/outcome info, and recorded telemetry
agree. Both retain 83 units and report `first_ledge_v1=True`; neither completes
the game. This is a selected learned-controller outcome under a declared noise
stream, **not** a held-out robustness test or general climbing competence.
Checkpoint download provenance and original game/environment fingerprints are
checked before loading. Evidence:
`artifacts/trusted_ledge_policy_20261003T224013267424Z/` and
`artifacts/policy_fidelity_20261003T224034122281Z/`.

### Secondary edge-support and inference-portability limitation

The replacement seed-2 `action_noise_5` evaluation remains at about
`(296.15,104)` but never satisfies v1's central X region. A coordinate-only
scan identified it as a candidate, not certified support. Replaying its exact
recorded remote actions for 384 ticks verifies real secondary platform support
by 7.13 game seconds, with **zero** measured local-fast/reference telemetry
error and **zero** remote-recorded body-position error at decision boundaries.
Evidence: `artifacts/recorded_edge_replay_20261003T230135948311Z/`.

However, loading the same trusted replacement checkpoint/normalizer for local
closed-loop inference does **not** reproduce that edge landing. Its predicted
action first differs from the remote trace at decision 2 by about 6e-8, while
body positions still agree then. The local fast/reference closed-loop traces
agree with each other but finish near `(88.59,38.04)` after 96 decisions.
Evidence: `artifacts/learned_edge_audit_20261003T225954450734Z/` and
`artifacts/v2_edge_policy_20261003T225850873712Z/`.

This separates reproducible recorded-action physics from a brittle portable
policy-inference outcome. Numerical inference/observation sensitivity is a
candidate cause; its exact origin is not yet isolated. Do not claim a portable
edge skill or alter the pilot gates. Future robust-policy studies should include
fixed-input inference comparisons and tiny-action/observation perturbations,
not just backend equivalence or selected seeded-noise success.

### Causal check of early action drift

The first body-position difference in the local/remote edge comparison occurs
at decision 7, about 0.00125 world units. Target differences grow above 0.01
pixel at decision 10, above 0.1 pixel at decision 15, and above 1 pixel at
decision 16; they later reach about 254.71 pixels within the 96-decision window.

A bounded three-case exact-game replay tests the recorded baseline, changing
only decision 7's X target by about 0.000252 pixel, and substituting all first
seven local applied targets (maximum change about 0.00253 pixel) while retaining
the recorded suffix. **All three still hold the platform**, retain 83 units,
and have zero measured fast/reference error. The perturbed final X positions
differ from baseline by less than 0.001 unit.
Evidence: `artifacts/action_sensitivity_20261003T231829646100Z/`.

Thus those early tiny action changes alone do not destroy the landing under
the fixed suffix. The failure involves later closed-loop amplification, rather
than a demonstrated catastrophic open-loop physics sensitivity at the first
drift. Exact observation/network/normalization causes remain unisolated.
Prioritize fixed-input inference and observation-path diagnostics, and robust
reactive control, before declaring that higher sampling rate or more compute
is the solution. These are post-hoc causal diagnostics, not policy promotion.

### Fixed-input inference fixture

A local-only `research.inference_probe` extracts continuous next-observation/
next-action pairs from saved policy traces, rejects auto-reset boundaries,
and hashes the normalized float32 fixture and trusted model. It runs no
physics and no training. This creates a portable fixture for a later
paused-host comparison without changing current inference or the live image.

On 95 fixed 217-dimensional inputs from the failed local edge rollout,
singleton inference reproduces its recorded actions **exactly**, including
repeat calls and tested thread counts 1/2/4. Batch sizes 8/95 produce maximum
normalized-action differences about 6.56e-7 /6.85e-7 (pointer differences below
0.000088 pixel). This demonstrates within-host inference-level rounding
differences under batching, independent of feedback/physics.
It does **not** establish that batching or thread count caused the live
remote/local divergence; the live evaluator uses singleton inference.
Local Torch is `2.6.0+cu124` running on CPU; deployed Torch is `2.6.0+cpu`.
Evidence: `artifacts/inference_probe_20261003T235912700282Z/`.
All **98 Python tests plus JS checks** pass. The source is local only and must
not be deployed during the current pilot.

## Conditional next-study preparation

`research.timing_study` now prepares a **non-executing** predeclared timing
comparison, conditional on finishing the pilot with no eligible follow-up.
It is not a launch, promotion, new reservation, or modification of the pilot.
Plan: `artifacts/timing_study_20261004T004121165329Z/plan.json`.
All **103 Python tests plus JS checks** pass.

PPO/absolute repeats 1/4 use new training seeds 3/4/5, the same original game,
terrain/raw settled reward/ordinary start, matched nominal 393,216 controlled
physics-tick budgets, 400-second episodes and 60-second evaluations.
One-tick decisions are 393,216 versus 98,304 for four-tick decisions.
Rollouts/minibatches are 8,192/1,024 versus 2,048/256, keeping 48 rollouts,
10 epochs and 3,840 planned optimizer calls per run. Gamma **and GAE lambda**
are scaled to equal physical-time decay. Warm-ups and noise offsets are held
for the same physical durations, not the same number of decisions.

This is not equal FLOPs or identical gradient information: the one-tick arm
has four times more decision/gradient sample presentations and observation/RPC
overhead. Terminal short steps can also change actual exposure; report actual
controlled ticks and reset-settling ticks separately. Do not mislabel nominal
budget matching as identical realized physics exposure.

The plan requires timing-aware trainer/evaluator/perturbation implementation,
frame-skip-specific fidelity and smoke checks, physical calibration of a
separate platform-support diagnostic alongside frozen v1, and a new bounded
session/reservation before it can execute. The preparation module cannot
launch training or bypass current campaign gates. If the remaining pilot
produces a legitimately eligible variant, prioritize its gated follow-up
instead of automatically executing this conditional plan.

### Secondary-detector physical calibration completed

A bounded **placement-only calibration**, explicitly `NOT_POLICY_SUCCESS`,
tests proposed platform-support X positions 285,290,296,320,340,345 by dropping
the body from Y=150 through original gravity with neutral pointer commands.
All six settle near Y=103/104 and pass the three-second/body-contact/speed
secondary detector. Only central X=320 passes the original narrow v1 region.
Outside positions X=250 and X=360 settle on low ground and fail; a 60-tick
contact window at `(320,104)` fails the three-second requirement.
All nine reference/fast calibration traces have zero measured telemetry error.
Evidence: `artifacts/support_calibration_20261004T011827646610Z/`.

This validates the secondary descriptor at the sampled physical positions and
negative cases, not every possible contact/trajectory or learner performance.
It remains separate from ordinary-start policy outcomes and does not alter
pilot reward/gates. The conditional timing study's calibration prerequisite
has evidence; timing-aware implementation, further preflight, finished-pilot
admission, and a new budget/session are still required before any launch.

### Physical-time perturbation controller prepared

`research.case_clock.PhysicalCaseClock` is a local-only future-study helper.
It indexes legal warm-up targets and seeded action-noise offsets by controlled
physics ticks. It reproduces the existing four-tick evaluator's applied actions
exactly for all nine declared cases, and gives one-tick control the same
four-tick noise offset cadence while allowing its model prediction to update
every tick. Warm-up lasts 12 physical ticks in either arm, not 12 one-tick
decisions. Clock regression/repeated calls/skipped blocks are refused.

All **109 Python tests plus JS checks** pass, including old-evaluator equality,
shared noise streams, held-noise/changing-policy separation, warm-up duration,
and noise-after-warm-up behavior. It is not integrated into the live evaluator,
does not execute the conditional plan, and is not deployed. Timing-aware
trainer/evaluator integration and fresh fidelity remain outstanding.

### Timing-aware evaluator integrated locally

`research.train.evaluate` now accepts explicit one/four-tick control and an
opt-in physical case clock. One-tick evaluation refuses legacy per-decision
perturbations or incompatible policy/normalizer/reward discounts. The default
four-tick path preserves existing case descriptors, trace rows and record keys.
The opt-in `physical-case-evaluation-v1` records requested versus actual
controlled ticks and reset-settling ticks separately, including VecEnv's
automatic reset after terminal/truncated steps. Final info remains pre-reset.
Cleanup now also runs if prediction/stepping fails.

All **117 Python tests plus JS checks** pass. Eight new synthetic tests cover
legacy traces, one-tick warm-up/noise duration, frozen normalization, short
terminal steps, incompatible configuration and failure cleanup.
`research.evaluation_timing_probe` runs no training and caps its fixture at
128 controlled ticks per case. A 96-tick constant-action ordinary-start check
passes all nine declared cases for repeats 1/4: **18 exact reference/fast
evaluation trace matches**, zero measured normalized-observation error, and
exact legacy/new four-tick trace equality on both backends. Each case reports
96 controlled ticks and 240 initial/automatic reset-settling ticks.
Evidence: `artifacts/evaluation_timing_probe_20261004T024404911122Z/`.

This is evaluator/fixture evidence, **not policy success** or comprehensive
one-tick reactive-policy fidelity. It is local only, not deployed or wired
into the trainer CLI. Remaining next-study work: trainer timing/GAE/budgets,
actual training/reset exposure, secondary-detector integration, independent
closed-loop fidelity/smokes, runner and new bounded-session admission.

### Timing-aware trainer and physical-work accounting integrated locally

The trainer now has an explicit `--timing-study --frame-skip 1|4` path.
`research.training_timing.training_settings` derives its full-run budgets,
rollouts/minibatches, physical-time gamma/GAE and episode/evaluation horizons
from the prepared plan; it refuses changed full-run budgets, reward settings
or algorithm. Smoke reductions are labelled pipeline-only and also preserve
matched nominal physical time. Trace/checkpoint intervals use physical cadence.
The legacy path keeps its former PPO/SAC learner defaults and four-tick
evaluation semantics. Timing-study **remote execution is explicitly refused**
until the bounded runner/preflight admission is implemented. This is not a
reservation, deployment, new study launch or promotion.

`PhysicalWork` observes successful steps and resets without changing returned
observations/rewards/info. It checks actual tick differences against telemetry,
counts terminal short decisions, and reports controlled versus reset-settling
work separately. Training summaries/trace rows now retain this actual exposure;
preflight/evaluation/runtime boot work are explicitly outside that scope.
Synthetic tests cover auto-resets, short terminals, invalid telemetry and
bitwise PPO/SAC weight equality with accounting enabled.
All **128 Python tests plus JS checks** pass.

Two matched ordinary-start **pipeline-only** smokes use training seed 3,
256 one-tick versus 64 four-tick transitions. Each reports **256 actual
controlled ticks, 120 reset-settling ticks and four policy optimizer calls**.
Both frozen-reference evaluations use all nine cases before/after for 128
controlled ticks per case, plus 240 initial/automatic reset ticks. Saved model
and 217-dimensional normalizer reloads preserve matching gamma and each arm's
physical-time GAE. Both have zero ledge holds/full completions in these short
horizons; this is pipeline correctness, not timing effectiveness or learning.
Evidence: `artifacts/timing_trainer_smoke_20261004T0302556740868Z/`,
including `verification.json`. No remote settings or source changed.

Next bounded priority: secondary support integration alongside frozen v1 and
independent contact-rich one/four-tick closed-loop fidelity, then the distinct
bounded session/runner/preflight. Preserve the existing pilot artifact prefix.

### Secondary support and contact-rich timing fidelity integrated locally

`research.study_metrics` adds the calibrated platform-support tracker only
under an explicit future-study contract, before the first environment reset.
It retains the original v1 descriptor unchanged and refuses an already changed
tracker. The timing-study trainer, evaluator and policy-fidelity rollout all
use both declared metrics. Legacy runs retain v1 alone. This is diagnostic
info, not a reward term or extra observation. The original campaign aggregator
must continue rejecting a changed pilot metric contract; the future timing
runner needs its own source-pinned aggregation for the declared two metrics.

The independent fidelity rollout now supports saved one/four-tick timing
contracts, physical-time warm-up/noise and per-arm discounts. Its comparison
checks exact predicted/applied actions and outcome/reward info, normalized
observations, rewards and decision-boundary runtime telemetry.
`research.timing_fidelity` uses an **untrained observation-dependent network**
whose legal downward target varies with the current observation. It performs
no learning or placement, caps each case at 512 controlled ticks and can run
headless on a future isolated preflight host.

Six ordinary-start checks, repeats 1/4 times nominal/hammer-left/noise-2,
each consume 384 ticks and pass **zero measured reference/fast differences**
in normalized observations, rewards and decision-boundary numeric telemetry,
with exact actions/info and production-evaluator trace equality. Each has
368..383 hammer-hit ticks, 3..17 body-hit ticks and varying predicted actions.
Retained gains are approximately 18.65..21.67; all central/secondary holds and
full completions are false. This verifies a contact-rich feedback path, not
learned climbing, every intermediate tick, cross-host portability or upper
route fidelity. Evidence: `artifacts/timing_fidelity_20261004T032235733238Z/`.
All **137 Python tests plus JS checks** pass.

Matched trainer smokes after adding the diagnostic retain **bitwise-equal
PPO weights and frozen normalizer statistics** to the prior timing smokes.
Training traces and all nine before/after reference case traces are identical
except for added secondary-metric info. Both arms still count 256 controlled
ticks, 120 reset ticks and four policy optimizer calls, with 217 observations.
Evidence: `artifacts/secondary_metrics_smoke_20261004T0324127860597Z/verification.json`.
No remote source/settings, budget reservation or pilot artifacts changed.

Next bounded priority: implement a distinct timing-study runner/aggregator
that freezes seeds/arms/metrics, validates all settings and dependencies, keeps
optimizer/actual controlled/reset work explicit, and enforces new session/
deadline/cost/preflight admission. Do not remove the CLI's remote-study refusal
until that admission is complete and tested. Then reserve a bounded CPU Upgrade
session and preflight a fresh private source snapshot; CPU XL is not justified
by these correctness checks.

### Separate timing-study contract and artifact checker prepared

`research.timing_campaign` prepares/checks the timing study independently of
the frozen pilot aggregator. It has **no execute operation and launches no
learner or browser jobs**. Full command generation is only a plan; the trainer still refuses
remote timing-study execution. Its six declared runs are sequential paired
repeats 1/4 within training seeds 3,4,5, with the original prepared budgets,
both metric descriptors and independent frozen reference cases.

Preparation requires the complete contract-validated nine-run pilot with no
eligible variant and refuses an existing output directory. It fingerprints
the current source/assets and retains a digest of prior pilot evidence.
Latest preparation:
`artifacts/timing_campaign_20261004T034517908263Z/timing_campaign.json`.
This is not a paid reservation, deployment or launch.

The JSON-only checker validates fixed settings/reward/normalization, gamma and
physical-time GAE, dependency/source/game equality, 3,840 actual policy calls
versus the separate 480 internal counter, actual controlled/reset work and
terminal short-step accounting. It rejects impossible reset counts given
episode horizons, counts exposure separately from requested ticks, checks all
nine legal seeded warm-up/noise action streams, metric contracts/latched hold
times, outcome-height agreement, contact counts and retained-spawn consistency.
Missing companion JSONs remain incomplete. Smoke results cannot be study
evidence. Three complete distinct training seeds per arm are required before
worst-seed arm comparisons; no automatic scale or final-goal verification.
Binary model/normalizer object integrity and independent saved-policy replay
remain separate requirements, not things this JSON checker establishes.

All **146 Python tests plus JS checks** pass, including nine new synthetic
acceptance/refusal tests. Real complete nine-case before/after traces from
both matched smoke arms pass the physical case checker and are deliberately
rejected as full-study artifacts. The prepared campaign reports six missing
runs, no comparison or success. Checker evidence:
`artifacts/timing_campaign_20261004T034517908263Z/checker_verification.json`.
The original pilot goal checker still reports 0 worst-seed completion and no
candidate/final success. No remote source/settings or ledger changed.

Next bounded priority: implement/test the remote-only sequential executor and
worker admission for a fresh distinct session, using explicit persisted budget
and source/preflight evidence, secret-stripped children, final-flush/auto-pause
and interruption refusal. Do not remove the trainer's remote-study refusal
until that admission is complete and tested. Then reserve/preflight a new
private CPU Upgrade snapshot; never relaunch or extend completed v2.

### Remote-only execution/admission foundation tested locally

`research.timing_execution` now provides a sequential six-run executor API
and strict admission validation. It is **not wired into `space_worker` or the
trainer CLI**, has no command-line execution entrypoint, and was not invoked
against a real learner. The trainer still refuses remote timing-study runs.
This is a tested foundation, not a claim that live deployment admission is
complete. No new reservation, upload, variable change or restart occurred.

Admission binds a distinct `timing-*` session to the owned Space/artifact repo,
declared contract, independently verified pre-launch PAUSED assertion, one
never-sleep CPU Upgrade replica, and all eight declared preflight checks on
the admitted source/game snapshot. It requires one active, unclosed reservation
with the same immutable Space revision/start/deadline, at most 16 hours, and
the $10 cumulative ceiling counting other elapsed/reserved charges. Source,
failed/incomplete preflight, expired/changed budget or another paid session
is refused. The parent must gather/verify that context from actual HF/runtime
and ledger evidence; this pure validator does not authenticate arbitrary JSON.

Execution requires isolated Linux, effective CPU/RAM/disk capacity and matching
prepared source/assets. It creates an exclusive execution claim before any
learner; an existing claim/run directory blocks all silent resume/reruns.
Only the declared paired seed order is scheduled, with per-run deadline and
complete artifact validation, and no new run after failure. Parent credential
variables are removed from child environments. Only its newly owned process
group may be terminated. Learners stop with a **60-second finalization reserve**
before the paid deadline; worker integration still must bound final upload/
pause and persist interruption evidence before dispatch.

All **157 Python tests plus JS checks** pass, including 11 new admission,
sequential scheduling, credential, deadline and interruption fixtures.
The first test attempt had three Windows fixture errors caused by globally
mocking `os.name` and assuming POSIX process-group attributes. A scoped host
predicate and mocked POSIX signals fix the fixtures without weakening the
real Linux-only guard. No real processes or provider state were affected.

A non-executing check against the actual closed ledger rejects completed
`poc-20261004-v2` as nonfresh and an unreserved diagnostic `timing-*` session
as lacking a reservation. Evidence:
`artifacts/timing_execution_checks_20261004T040407335016Z/verification.json`.
The actual Space remains PAUSED on its original source; its deadline and ledger
were not edited.

Next bounded priority: wire/test the worker's fresh timing preflight and study
modes, persisted source/ledger/context transport and initial/terminal durable
status, and the trainer's narrowly scoped admission check. Keep the existing
pilot path and completed artifact prefixes immutable. Only after integration
passes locally should a new capped CPU Upgrade reservation/private snapshot be
preflighted, reviewed while PAUSED and intentionally launched.

### Worker/trainer timing admission wired and tested locally

Local `space_worker` now recognizes `timing_preflight` and `timing_study` only
for a distinct `timing-*` session on the owned Space/private dataset. The old
preflight/pilot paths remain intact. `deploy.timing_worker` reads only
`<session>/operator/timing_context.json`, pinned by **`RL_CONTEXT_REVISION`** to
one immutable dataset commit, with a 2 MiB JSON bound. Context must contain the
ledger snapshot and ticket for the new reservation plus pinned prior-pilot
summary/source evidence. It is not bundled or stored in source code.

For timing preflight, the operator ticket's `preflight` must be null and there
must be no persisted session status. Reservation/runtime/source checks occur
before any jobs. The eight actual check processes include unit/JS, raw physics
fidelity, reactive timing fidelity, benchmark/resources and both matched
pipeline smokes; they are not substantive training. Only successful checks
produce durable `preflight_complete` with `study_kind=timing` and the eight
passed flags. The worker then bounded-flushes and pauses.

To intentionally start a study, the operator must independently verify that
preflight and PAUSED, then publish a new pinned context whose ticket contains
the exact durable preflight fields and set the fresh session to `timing_study`
while PAUSED. The worker rechecks actual immutable Space revision, runtime,
source/game and persisted budget. It imports only bounded JSON from the
completed pinned v2 pilot, validates the old ineligibility evidence, prepares
a fresh timing campaign and durably records dispatch/claim **before learners**.
Interrupted/nonfinal statuses block all restart/resume. Completed/failed or
wrong-kind preflight evidence cannot start a study.

Each trainer receives a parent-owned grant binding its direct parent PID,
declared seed/arm/budget, new output path and immutable execution-claim hash.
Linux/context/ledger/source/preflight/deadline admission is checked before
model/browser creation. The manifest retains a small admitted-session record;
the timing aggregator rejects missing/mixed admission sessions and binds
results to the claimed execution. Smokes remain explicitly unadmitted.
The parent runs/terminates only its owned learner/browser process group,
removes credential variables, preserves the 60-second finalization reserve,
and guarantees bounded final flush/pause paths.

All **168 Python tests plus JS checks** pass. New fixtures cover pinned private
reads, preflight-only commands, stale/repeated/wrong-source contexts, durable
pre-dispatch synchronization, interrupted sessions, initial sync failure,
successful mocked study dispatch, direct-parent/argument/claim grant checks,
and refusal after an undurable claim. Completed/failed sessions are preserved
without overwriting or relaunching. The read-only monitor now distinguishes
timing runs from imported prior-pilot files and reports secondary support/
controlled-reset ticks when present. These are mocks, not live HF admission.

Two bounded real-game smokes still report 256 controlled ticks, 120 reset ticks
and four policy calls per arm. Their weights are bitwise equal to prior smokes;
all nine before/after reference traces pass the physical checker. They claim
no remote admission or competence. The allowlisted bundle includes both
integration modules without runtime contexts/ledger/artifacts.
Evidence: `artifacts/worker_admission_smoke_20261004T0425133084373Z/verification.json`.
No HF writes, source/variable changes, paid reservation or remote jobs occurred.

Next bounded priority: verify current CPU Upgrade pricing, reserve a unique
`timing-*` session within the $10 total ceiling (including preflight/build
elapsed time), build/publish the allowlisted private snapshot while preserving
PAUSED and completed v2, and upload its secret-free operator context. Keep the
same new-session start/deadline through preflight and study; never reuse/extend
v2's old deadline. Run only `timing_preflight` first and independently inspect
its immutable outputs and PAUSED state before any study mode change.
