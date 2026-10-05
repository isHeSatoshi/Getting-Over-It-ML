# Fresh residual-PPO study

The executable core is implemented in `research/residual_study.py`,
`residual_train.py`, `residual_evaluation.py`, `residual_execution.py`
and `residual_campaign.py`. This is a proposal and tested infrastructure,
not a trained climber or authorization to bypass preflight.

## Fixed proposal

- Training seeds12/13/14,131072 transitions per seed.
- Unchanged ordinary spawn, raw climb-v2 reward, frame1/horizon1800.
- Fresh online222 RMS from actual training contexts, frozen for evaluation.
- PPO rollout1024, batch128,3epochs, learning rate.0001, physical gamma,
  GAE `.95**.25`, clip.2 and targetKL.01. At most3072 optimizer calls and
  257 actual120-tick resets per seed.
- Save after completed updates at65536/131072; choose final only.
- Compare the same zero-actor baseline and final learner on nine predeclared
  reference cases: reset15001, nominal/left/right warm-ups, noise.02 with
  four-tick holds and seeds14100..14105.
- Two-hour/$0.06 proposed ceiling, under the cumulative$10 limit.
  **No reservation or paid batch is active.**

No forced warm-ups, external noise or supervised teacher labels enter
training. Evaluation perturbations act after the issued final command.

## Physical evidence and admission

Direct Gym evaluation performs one120-tick reset per case, without
VecEnv auto-reset. Full traces preserve raw217/actor222, residual,
issued/applied actions and actual original physical states. Holds are
reconstructed from geometry, speed and body-query fraction, not reward.
Bounded per-case JSON files use a hash/size/path-checked index; a single
combined nine-case trace could exceed the JSON byte limit.

The learned first-ledge benefit gate requires every seed's nominal hold,
at least8/9 central holds, no extra deaths/lower median retained height,
and an additional hold or full completion versus the same baseline.
Baseline holds are hand-designed. Full-climb completion, independent
held-out cases, upper-route fidelity and saved-policy replay remain separate.

Full training requires a fresh Linux direct-parent grant binding current
source, prior, context, passed preflight, independently verified PAUSED,
one never-sleep CPU Upgrade replica, explicit reservation and immutable
deadline. Existing claims or outputs cannot resume. Sequential dispatch
validates and backs up each run before the next, then requests owned
auto-pause. The deployment worker must supply those durable/pause callbacks.
Worker/dispatcher wiring is the next step, not implemented yet.

## Completed checks

24 new/423 full Python tests,16 counter JS tests and collision JS pass.
The frozen smoke uses **only a synthetic mock without a game bridge**:
8 toy transitions,2 optimizer calls and120 mock reset steps. These are
not original-game training or physical success. A failed toy expectation
of2 calls under KL early-stop is preserved; only the separate tiny mock
disables early-stop. Full-study KL.01 remains unchanged.

The bounded storage correction has a separate hash-bound amendment.
It preserves the completed smoke plan and proves learning/init/accounting
code unchanged. No repeated mock experiment or extended deadline.
Evidence: `artifacts/residual_research_contract_20261005_v1/verification.json`
and `storage_amendment.json`.
