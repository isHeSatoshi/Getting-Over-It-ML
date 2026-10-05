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

Next implement/test the separate Gym222 residual adapter, correct terminal
and time-limit observations, zero actor mean initialization/logstdlog(.01)
and fresh normalizer/checkpoint contracts, without a local optimizer.
Only then prepare a fresh bounded private three-seed residual-PPO batch.
Any learner benefit must beat this exact zero-actor baseline. Full-climb,
held-out, upper-route fidelity and saved-policy goals remain unchanged.
