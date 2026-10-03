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

## Current remote experiment

- Private Space: `isHeSatoshi/rl-over-it-poc-20261004`.
- Private artifacts: `isHeSatoshi/rl-over-it-research-artifacts`.
- Dataset session: `poc-20261004-v1`.
- Deployed revision: `b3bf197090f1fb5219e5cce70a0dbfcca6576ce1`.
- Tier: CPU Upgrade, one replica, sequential nine-run pilot.
- Persisted deadline: **2026-10-04 12:21:08 UTC**, epoch `1791116468.8050392`.
- PPO/absolute, SAC/absolute, SAC/velocity, seeds 0/1/2, 98,304 transitions
  each. Four-tick actions, settled reward, terrain, raw rewards, common
  physical-time discount, reference evaluation.

Do not modify, upload, restart, or resize this running image. A stale uploaded
log is not a stalled learner: continuously appended files can be skipped by
its stable-file backup rule. Stable checkpoints and completed files still
upload. The append-only snapshot fix is local and tested, not deployed.

Finish and validate this pilot first. Its original gates remain unchanged.
If it fails, a new diagnostic experiment is allowed under the newly delegated
authority, but is **not** a promotion of the failed pilot.

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
- The 20k checkpoint visibly controls the real hammer and moves to about
  `(109.28,79.70)` in a short nominal trace. It is brittle. An evaluation's
  post-reset screenshot must not be presented as its final policy pose.
- Latest baseline validation: 60 Python tests and JS collision tests pass.
- PPO `training_summary.gradient_updates` currently stores SB3 `_n_updates`,
  an epoch count, not individual minibatch optimizer steps. Correct and
  version this measurement in the next source snapshot, not the live image.

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
