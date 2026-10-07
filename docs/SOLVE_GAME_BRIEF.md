# Handoff: make an ML system beat Getting Over It end to end

You are taking over a project that has burned six full training campaigns and
~28 CPU-hours and has never gotten past the first ledge. Your job: produce a
policy that climbs from the ordinary spawn to the summit, the entire game, on
the real game runtime. This brief tells you what was tried and failed so you
do not re-tread it. How you solve it is up to you.

**Repo:** `https://github.com/isHeSatoshi/Getting-Over-It-ML` (branch `master`).
Clone it first; everything referenced below is committed there.

**Goal:** world `Y > 16000` from the ordinary spawn (the game's own win
condition). The first ledge (`X 305-335, Y 100-112`) is ~0.5% of the climb;
every previous attempt died there. The summit is the target, not the ledge.

**Machine notes:** the harness runs the real compiled game, so this machine
needs Chrome/Chromium (see `docs/FAST_BACKEND.md`). All previous work ran
single-threaded CPU; if this machine has a GPU, use it. Read
`docs/RESEARCH_AUDIT.md` (physics audit) and the `Result:` sections of
`autoresearch.md` (full experiment journal) before planning. The game has no
time limit; a human full climb takes 1-2 hours, so do not cap episodes at the
few-minute horizons earlier experiments used.

## Environment facts (fixed)

- Real game: Scratch project 389464290, compiled, real renderer, real
  silhouette collisions. Stubbed or simulated physics is invalid and the
  legacy paths that did it are disabled in this repo.
- 30 physics Hz, 4 physics ticks per decision (7.5 decisions/s).
  Action: `Box(-1, 1, (2,))` = player-relative pointer offset, scaled by 128,
  held 4 ticks. Observation: 217 `float32` (26 physical + 63 reward history +
  128 terrain rays).
- Spawn `(0, 21)`. Summit `Y > 16000`. Death `Y < -180`.
- Measured runtime: ~266 decisions/s (~1065 physics ticks/s) with terrain on.
- Tests: `python -m unittest discover -s tests -p "test_*.py"` (511 tests)
  plus `node tests/collision_memo.test.js`. Run them before trusting a number.

## What was tried and failed

1. **Simulated physics backends.** A Node port and a "physics server" stubbed
   out collisions, so early "learning" was garbage (policies scored heights
   that do not exist). Permanently disabled. Async browser stepping was also
   unusable for control; only the compiled in-page fast path is validated.

2. **Hand-designed controllers (not learned).** One causal controller holds
   the first ledge at `(322.59, 104)`, +83 units retained, 0 deaths. It was
   found by plan search in pointer space. Dozens of follow-up controller
   experiments (pressure/contact designs, recenter, stroke, terminal,
   source-goal, residual variants) all failed to extend it. Above the ledge
   there is no controller, no recorded route, and no data at all.

3. **Goal-conditioned SAC + HER (six campaigns, ~28 CPU-hours, ~$0.83).**
   Every campaign: 0/10 first-ledge holds, 0 summits. Best-ever learned reach:
   `Y 96.1` at `X 279` (one infrastructure-killed run briefly touched `Y 100.6`
   - a high-water mark, not a result). Failure modes measured:
   - Fixed-point collapse: the policy climbs to the wall (`X ~279`) then
     freezes; the game clock advances, the position does not.
   - Exploration barrier: the wall-to-ledge move is a coordinated ~120-tick
     swing. Policy exploration noise (sigma ~0.09) essentially never samples
     it; the demonstrated motion needed sigma ~0.5.
   - More data did not fix it: 160k transitions and 480k transitions failed
     the same way. The trainer was single-threaded CPU; SAC update compute
     dominated wall time (480k transitions ~= 6 hours).
   - Seeding exploration with action bursts replayed from the one recorded
     climb (600 ticks, spawn to ledge) was tried at two burst lengths.
     Short bursts improved early retention (all 10 cases positive, nominal
     +43.5 units) but never produced a hold; longer bursts regressed route
     progress (nominal +2, no case even reached the wall). Dead end.

4. **Imitation / trajectory transfer.** Replaying recorded actions did not
   transfer to learned control; cross-host portability gates failed.
   Matched-host inference was repeatable but produced no climbing. A per-tick
   trajectory that reaches the ledge exists, but resampling it to the 4-tick
   decision interface fails - the control bandwidth is a real constraint.

5. **Reward and clock pitfalls (fixed; do not regress).** Per-decision
   discounting (0.99 at 4 ticks / 30 Hz) gives a 9.2-second half-life while
   the climb takes minutes; early runs had no effective gradient to distant
   progress. The harness now discounts in game time (120 s half-life).
   Transient height is never progress; only a retained hold counts.

6. **Budget lesson.** Brute-force multi-hour CPU training produced zero
   progress past `Y ~100` across six campaigns. Do not start another one.

## Untouched ground (unknown, not recommendations)

- No route data beyond the first 600 ticks; everything above the ledge is
  unmapped. The game can be driven and recorded through the harness.
- Plan search (MPPI/CEM) in pointer space was only ever run by hand for the
  ledge; never scaled or automated for a full route.
- No learned residual on top of the known-good ledge controller.
- No longer-horizon action parameterization (multi-tick strokes) to bypass
  the 4-tick bandwidth limit.
- No GPU-scale training; all campaigns were CPU-bound.

## Definition of done

A policy that reaches `Y > 16000` from ordinary spawn on the real runtime,
reproduced across seeds and evaluation cases that were not used for training,
with the saved policy, a replay, and the exact command that produced the
numbers. High-water marks and partial climbs are not results.

Every number must come with the command and trace that produced it.
`autoresearch.md` records the full history; read it before planning.
