# Goal-conditioned SAC / HER / legal-prefix curriculum

This implements the replacement design from session
`2e405d38-60cd-4412-b784-732ab4e4d1c2`, including its clarification in
`artifacts/goal_design_handoff_20261005_v1/clarification_reply.txt`.
The residual-PPO route is inactive. Its unfinished files were preserved.

## Post-build correctness review

The review after `6e5c3f9` preserves SAC/HER, the fixed observation/reward,
physical gates, prefix tolerances and all budgets. See `GOAL_REVIEW.md`.
Verified nominal prefixes retain consistent immutable causal records when
numerical differences are inside tolerance. Fall recovery keeps its
original candidate boundary until reacquisition, rather than cascading
backward on identical observations. Backup callers serialize before their
individual upload timers start, while retaining the absolute deadline.

Insufficient physics budget for another full return/suffix plus evaluation
now finalizes the learner and performs the already-reserved evaluation.
It reports `complete=false`, `stop_reason=physics_reserve`; the physical
result remains visible but cannot promote the seed or start another one.

## Implemented contracts

- `research/goal_env.py`: unchanged real physics and controls, separate local
  goal reward, fixed155-feature frames stacked oldest-to-newest into620.
  Inputs exclude query flags, reward history and hidden source phase.
  Reset repeats the first actual frame; legal prefixes populate real history.
- `research/goal_replay.py`: capacity300000, issued actions (not substituted
  noisy commands), original and HER transitions. Exactly half the sampled
  slots request strictly later nonterminal goals from the same suffix.
  All eight historical goal-coordinate pairs are reconstructed. Warm-ups
  are ineligible for actor/critic/HER and excluded from learner/update
  scheduling counts, but consume total physics budget. Death keeps original reward and no
  bootstrap; true time limits use their actual final observation.
- `research/goal_archive.py`, `goal_curriculum.py`: actual legal reset and
  full-prefix replay, tick/frame/seed/endpoint/history verification,
  25-unit cells and hammer octants, at most256 cells/two representatives.
  Prefixes are capped at1800 ticks and hash-chain every command, state and
  history. No snapshots are injected into the game. Perturbed endpoints
  have their own realized prefixes/provenance.
- `research/goal_train.py`: CPU SAC,128/128 ReLU actor/twin critics,
  lr.0003, batch256, tau.005, gamma.995, auto entropy/target−2.
  The first4096 eligible learner transitions have no updates; then one cycle per
  two eligible learner transitions, at most77952. Counts actor, critic and
  entropy optimizer calls separately.
- `research/goal_evaluation.py`: ordinary-spawn learned-only3600-tick
  reference cases. Supervisor supplies stable waypoint goals, never mouse
  playback. Stable anchors need30 ticks within12 units at speed≤2; first
  ledge also requires its original90-tick milestone. Falls select earlier
  waypoints. Physical gates and causal observations are independently checked.

## Pilot, not summit success

Seeds21/22/23 run sequentially, sharing only historical opening scaffolding.
Each gets at most160000 learner transitions and1.2million total physics
ticks including prefixes, resets, preflight allocation and evaluation.
Ten fresh reference cases: reset18001, nominal, left/right12-tick warm-ups,
noise.02 held four ticks with seeds17100..17106.

Each seed must achieve nominal first-ledge success, at least8/10 existing
first-ledge successes, and a continuous nominal learned rollout retaining
Y≥180 for90 consecutive ticks at speed≤2. No teacher prefix/controller or
action playback is used for scoring. Stop after the first failed seed.
The pilot is not a summit claim. Final three-seed summit, untouched held-out
reference cases, upper-route fidelity and saved closed-loop replay remain
required.

Session cap: **$0.30 or ten paid hours, whichever comes first**, within the
existing cumulative$10 ceiling. Reverify current CPU Upgrade price.
No training or reservation was created by this build.

## Execution integration

`deploy/goal_worker.py` plugs into the existing private Space worker as
`goal_preflight` / `goal_study`. It reuses pinned private inputs,
secret-stripped children, resource/runtime checks, durable backups,
watchdog and auto-pause. `research/goal_campaign.py` provides pure helpers
for reservations/contexts/approval, without making remote writes.
`research/goal_run.py` requires a fresh live-parent Linux grant.

Preflight runs active unit checks, collision tests, one-simulator resource
measurement/benchmark, goal pipeline and legal-prefix-plus-feedback
reference/fast fidelity. Full training needs durable passed preflight and
independently verified PAUSED before intentional mode change/restart.

Model checkpoints contain actor/critics/optimizers, compressed replay,
compressed prefix archive, RNG state, fixed schema, waypoint supervisor,
source/assets and file hashes. Verify trusted checkpoint hashes before
loading. Do not silently resume an interrupted pilot.

## Pilot attempt 1 (stopped 2026-10-05)

One bounded pilot ran from the reviewed tree plus the platform-guard test
fix (deployed source `01eace30e5561321efb1f14bdcb4a342af87bd9c`, session
`goal-20261005-v1`, reservation `$0.30`/10h at verified `$0.03`/h). A first
preflight failed on one platform-dependent inactive-residual test; its
evidence is preserved and the clean re-run passed all six checks. Seed21
reached 39936/160000 learner transitions and 17920 SAC cycles, then the
first checkpoint crashed writing `supervisor.json` because `waypoints()`
emitted `np.bool_` for non-central anchors. No physical evaluation ran;
seeds22/23 never started; the worker auto-paused and the reservation was
closed at about `$0.0232` elapsed of `$0.30`. Fix: explicit `bool()` casts
in `waypoints()` and a regression test that serializes non-central anchors
exactly as the checkpoint writer does. The fix is validated locally but
has not been deployed or re-run; a retry needs a fresh session and
reservation, never a resume or deadline extension.

## Validation performed

Post-review and pilot-fix: **462 active Python tests passed**, including
seven new regression tests (six from the review, one for the pilot crash),
plus all16 counter JS tests and collision JS. The same12 unfinished
residual-worker tests remain explicitly excluded. Review validation used
unit/mock checks only, without original-game rollout, training, deployment,
HF API calls or paid compute. The revised source requires new remote
preflight; old original-game fidelity evidence below is not a new-source pass.

Original build validation:

- 455 active/established Python tests passed, plus16 counter JS tests and
  collision JS. Twelve tests from the canceled, unfinished residual worker
  are explicitly excluded by `python -m research.goal_checks`.
- Full unrestricted discovery exposed one inactive residual fixture failure;
  its files were left untouched. That is not a goal-pilot gate failure.
- Goal pipeline passed a bounded synthetic SAC update and saved actor reload.
- Original reference/fast legal opening + exact prefix replay +60 ticks of
  untrained closed-loop feedback passed:2520controlled +720reset/bootstrap
  ticks,3240 total,85.73 seconds, one simulator at a time.
- No original-game learner was trained; no climbing improvement is claimed.

Windows CUDA Torch import temporarily failed because the existing paging
capacity was exhausted. Validation used an isolatedCPU Torch2.6.0 test
environment under `artifacts/goal_build_20261005_v1/cpu_testenv`, inheriting
the repository dependencies. Original venv/system settings/unrelated
processes were not changed. A fixture float32 mismatch and a missing
Selenium dependency in that temporary environment were corrected; the
failed bounded fidelity attempt ran no game ticks and its log was retained.

## Runner commands

Local correctness, no paid compute:

```powershell
cd D:\Project\cat
& .\artifacts\goal_build_20261005_v1\cpu_testenv\Scripts\python.exe -m research.goal_checks
node .\tests\procedure_counter.test.js
node .\tests\collision_memo.test.js
```

Fresh private deployment tree, never profiles/logs/credentials:

```powershell
& .\artifacts\goal_build_20261005_v1\cpu_testenv\Scripts\python.exe -m deploy.bundle
```

Do not invoke `goal_run` directly on the desktop. Use the private worker and
fresh admission. The old94-invocation research loop stays canceled.
