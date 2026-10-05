# Residual control scaffold

`research/residual_controller.py` wraps the unchanged
`StrokeController(mode="contact_timed_feedback")`. It is infrastructure
for a future learner, not a trained policy or validated teacher.

## Actor and action contracts

The actor input has 222 float32 features:

| Slice | Meaning |
|---|---|
| `0:217` | Actual raw pre-action game observation |
| `217` | Current selected source phase divided by 599, clamped at 1 |
| `218:220` | Current legal base proposal |
| `220:222` | Previous OWN issued final command, initially zero |

The raw217 input to the base is never normalized. Only a future actor
input may use a new222 RMS. `validate_normalizer` checks the entire
scaffold contract and finite222 statistics; old217 normalizers fail.
No case identity, seeds, future noise or privileged counters are inputs.

The residual command is two float32 axes in `[-1,1]`. Final control is
`float32clip(base + 2*residual, -1, 1)`. Thus zero residual reproduces the
base and a nonzero residual can override it across the full legal range.
Original motor, reach, collision solver and reward remain untouched.

## Lifecycle and provenance

1. `reset(actual_raw_reset_observation)` after an actual environment reset.
2. `prepare(actual_pre)` obtains the actor context and advances the base
   exactly once. Repeated preparation of the same pre returns a copy.
3. `action(legal_residual)` issues one final command.
4. `observe(actual_post, actual_applied, terminated=..., truncated=...)`
   records the actual transition before another action.

Next pre must equal the last actual post. Horizon1800 and terminal
guards prevent further actions until reset. Inputs, outputs and nested
diagnostics are copied. Controller reset does not reset or place the game;
the caller must verify real episode resets and one-tick physics.

Records distinguish base proposal, legal residual, unclipped final,
issued final and externally applied command. Own history means the issued
final, even when forced warm-up or noise changes actual application.
Clipped or ignored proposals are not physical teacher labels.

## Completed zero-actor validation

- 16 new tests; 381 full Python tests; 16 counter JS tests; collision JS pass.
- 2,702 saved nominal600/failed751 reference/fast rows: zero-action bytes,
  base metadata and causal actor context match exactly.
- Four frozen nominal600 baseline/zero-actor reference/fast rollouts:
  2,400 control ticks,480 episode reset plus240 bridge bootstrap ticks,
  31.903158 seconds. All archived physics/actions/raw217/rewards/infos/base
  metadata, backend pairs and baseline/scaffold physical histories match.
- Both reference arms finish `(322.585886,104)`, retained gain83, central
  and secondary holds. Zero deaths, summits and optimizer updates.

Those holds belong to the same hand-designed baseline. **No learned
improvement or reliable learned climber is demonstrated.** The failed
saved trajectory still retains gain11 and has no holds.
Evidence: `artifacts/residual_scaffold_fidelity_20261005_v1/verification.json`.

## Gym adapter and actor initialization

`research/residual_env.py` now implements the separate Gym222 adapter.
It accepts only the unchanged absolute/frame1/horizon1800/raw217 game
configuration. It preserves raw climb-v2 reward, validates actual tick
and applied command memory, and records separate issuance/application.
Optional evaluation perturbations act after final control issuance and
never enter the actor context as seeds or future noise.

Returning an observation does not call the base. A pure preview of the
unchanged correction equation computes next proposal/source phase/own
history. Inside the next actual step, scaffold preparation must match
that preview byte-for-byte. This avoids an extra hypothetical base call
at time limits. Terminal222 uses the actual final raw217 and continuing
clamped proposal/history; DummyVecEnv preserves it before actual reset.
Future PPO can bootstrap time limits without a217/222 dimension mismatch.

`research/residual_policy.py` provides `ZeroResidualPolicy`, compatible
with PPO, `[256,256]`, exact zero mean-head weight/bias and
`log_std=log(.01)`. Initial residual standard deviation is `.01`, giving
`.02` final command deviation before clipping. Reload loads saved weights
after construction, so a nonzero saved head is not accidentally reset.

Fresh222 VecNormalize defaults to raw rewards, infinite reward clipping,
physical-time gamma, observation clip10 and epsilon1e-8. Checkpoint
metadata binds source, prior arrays, adapter/policy/scaffold schema and
matching RMS. Standalone replay requires an actual reset; these weights
do not constitute a mid-episode game-state restoration.

Validation:18 new/399 full Python tests and both JS checks pass.
One frozen2702-row saved/mock pipeline verifies nominal600/failed751
contexts and commands on both backends. Three initialized actors
(seeds12/13/14) make8106 deterministic-zero predictions,192 reload
predictions and192 distribution checks. Model/RMS/parameters reload
exactly; zero optimizer calls/timesteps, zero new gameplay/reset ticks.
All four archive endings are explicitly mocked time limits, not actual
original-game endings. Fresh RMS statistics fitting is not policy training.
Evidence: `artifacts/residual_adapter_pipeline_20261005_v1/verification.json`.

The fresh three-seed residual-PPO study/trainer/admission core is now
implemented, including bounded actual physics/optimizer accounting and
hash-indexed per-case reference traces. See `RESIDUAL_STUDY.md`.
No original-game training or paid reservation is active yet.
Next integrate the owned private worker and preflight. Any learner
benefit must beat this exact zero-actor baseline. Full-climb, held-out,
upper-route fidelity and saved-policy goals remain unchanged.
