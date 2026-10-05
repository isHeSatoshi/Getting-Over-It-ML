# Goal-SAC implementation review

Reviewed the implementation in `6e5c3f9` against the approved goal-SAC/HER
design and its five clarifications. The design remains an unproven,
bounded learning hypothesis, not evidence that the game or ML challenge
has been solved.

## Confirmed issues fixed

1. **Physics-cap finalization.** Previously, insufficient budget for another
   return/suffix raised before the final checkpoint and reserved evaluation.
   It now saves and evaluates the partial learner, reports
   `complete=false`/`stop_reason=physics_reserve`, and stops the campaign
   without admitting another seed. Physical outcome and pilot admission are
   separate fields. Update accounting is checked against actual transitions.
2. **Prefix hash consistency.** Nominal replay could pass the physical
   tolerance but mix newly measured route states with original snapshots
   and their original hash chain. Extensions then failed integrity checks.
   Verified nominal records now remain internally consistent; perturbed
   returns still retain their own actual records and parent identity.
3. **Fall recovery.** Repeated identical low observations shrank the recovery
   candidate set and pushed the target farther backward. The candidate
   boundary now stays fixed until reacquisition. Actual further movement
   can still select a nearer recovery waypoint within that boundary.
4. **Backup contention.** A caller's upload timeout previously included
   waiting for another healthy upload. Goal backups now serialize before
   starting that timer, without extending the campaign deadline.

Six regression tests cover tolerated-drift extension/replay, repeated and
deeper falls, budget-stop finalization, incomplete-seed admission, concurrent
backup timing and expired-deadline refusal.

## Validation and limitations

- `python -m research.goal_checks`: **461 passed**.
- `node tests/procedure_counter.test.js`: **16 passed**.
- `node tests/collision_memo.test.js`: **passed**.
- The same12 unfinished/inactive residual-worker tests are explicitly
  excluded, not fixed or represented as passing.
- Used the existing isolated CPU test Python under
  `artifacts/goal_build_20261005_v1/cpu_testenv`.
- No original-game rollouts, game training, deployment, scheduled loops,
  HF API calls or paid compute were performed in this review.
- HF's last reported PAUSED state was not independently rechecked here.
- Existing user changes and the unfinished residual integration were
  preserved. These review changes are in the working tree, not a new commit.

## Execution decision

Proceed only to the **fresh preflight and bounded pilot** described in
`GOAL_RUNNER_PROMPT.md`, using the reviewed source, not `6e5c3f9` alone.
The old preflight cannot admit the revised source. Preserve the $0.30 /
ten-hour limit, sequential seeds, first-failure stop and original physical
gates. There is no automatic next reservation or indefinite research loop.

The remaining scientific question is whether local goal learning plus
legal-prefix practice produces reliable recovery and progress beyond the
opening. Only original-game learned-policy evidence can answer it. The
pilot's Y180 gate is not a summit, and passing it does not establish the
three-seed held-out full-game success criteria.
