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

## Current remote state: pilot complete and paused

- Private Space: `isHeSatoshi/rl-over-it-poc-20261004`.
- Private artifacts: `isHeSatoshi/rl-over-it-research-artifacts`.
- Active dataset session: `poc-20261004-v2`.
- Active deployed revision: `34c35854133294f97fef741479641f571371b8a3`.
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
revision is still deployed; no local diagnostic changes were uploaded.
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
These estimates are not the actual provider bill. There is no active paid
research batch. Keep the operator running for useful bounded research work.
Do not restart the completed pilot or overwrite either artifact session.
The next priority is the predeclared timing diagnostic, not promotion or
blind sample/hardware scaling. Complete timing-aware trainer/GAE/horizon,
actual training/reset tick accounting, independent closed-loop fidelity/smokes,
and a runner with new session/budget admission before any launch.

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
