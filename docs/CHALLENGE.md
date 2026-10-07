# The Getting Over It Open RL Challenge

**Beat a hand-designed controller at Getting Over It using learning.**

This is an open challenge, not a research result. The environment, the scoring,
and the gates are fixed and published. The RL method, the algorithm, the
architecture, the curriculum, the exploration strategy, and every other detail
are yours to choose.

---

## Why this challenge exists

Getting Over It is a physics game about *precise manipulation under contact*.
You do not move the character directly. You move a mouse, and the character
follows because the hammer catches terrain. That makes it a genuinely hard
control problem, and it has resisted RL.

This repository ran four serious RL campaigns against it. Every one scored
**0 of 10** on the first-ledge milestone. In the most recent run, the best
nominal policy retained **+2 units** of height.

A hand-designed causal controller on the same harness reaches and holds the
first ledge at **(322.59, 104)**, retaining **83 units**, with zero deaths.

So the bar is set by a controller, not by a learned agent. **Your job is to
cross that line with learning.** Not to tune a reward until something moves.
Not to show a high-water mark. To actually hold the ledge.

## What makes the measurement trustworthy

Most "solved this game with AI" claims are not checkable. This one is built so
that a claim either holds up or does not:

- **The original game runs.** The actual compiled Scratch project executes in a
  real renderer. Physics is never approximated, reimplemented, or stubbed.
  An earlier attempt in this repo did stub it, and its results were garbage.
- **Every telemetry claim is cross-checked per tick.** Tick ordering, frame IDs,
  applied command IDs, the 30 Hz virtual clock, velocities against measured
  displacement, and world/camera frame consistency all raise on mismatch.
- **Scoring ignores flattery.** A transient height spike is not progress. See
  below.
- **Held-out cases are held out.** Nine public cases are published. Promotion
  requires passing 20 cases per seed that are not on the public set.

---

## The environment

| Property | Value |
|---|---|
| Game | Getting Over It, Scratch project 389464290 |
| Physics | original compiled project, real renderer |
| Rate | 30 physics Hz, **4 ticks per decision** (7.5 decisions/s) |
| Action | `Box(-1, 1, shape=(2,))`, a **player-relative pointer offset** |
| Action meaning | `action * 128` sets the pointer offset, held for 4 ticks |
| Observation | 217 `float32`: 26 physical, 63 reward history, 128 terrain rays |
| Success | world Y > 16000 (the game's own condition) |
| Death | world Y < -180 (the game's own condition) |
| Episode cap | 1800 decisions (240 game seconds) |

The action is a **player-relative offset**, not a world coordinate and not a
hammer screen position. This is easy to get wrong and it silently does nothing.

## Install

```powershell
python -m pip install -r requirements-research.txt
```

You also need Chrome or Chromium with a matching chromedriver, and the bundled
game assets (see `NOTICE` for their status).

## Run the checks

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m challenge.verify
```

`challenge.verify` proves the runtime is the real one and that the documented
causal checks still hold. If it fails, your numbers are not comparable.

---

## Scoring: what counts and what does not

### Tiers

A tier is passed only by **holding** a region: being inside the box, moving at
most 2 units/tick, with real body-contact query hits on at least 80% of ticks,
continuously for 3 seconds.

| Tier | Region (world) | Meaning |
|---|---|---|
| 0 | x ∈ [-20, 20], y ∈ [15, 30] | settle and stay put. The spawn point. |
| 1 | x ∈ [305, 335], y ∈ [100, 112] | **the first ledge. This is the headline goal.** |
| 2 | x ∈ [280, 300], y ∈ [100, 112] | the wall-side approach |

Tier 0 is a control. If you cannot score it, something is wrong with your
harness before anything is wrong with your algorithm.

### Never accepted as a result

- A transient maximum height without a retained hold.
- Shaped reward return from an unfinished episode.
- A single deterministic replay seed.
- Numbers measured on the accelerated backend without a reference-backend
  confirmation.

A worked example, measured on the real game: holding the pointer at `(0, -128)`
lifts the body from Y=21 to Y=100.4, which is *inside* tier 1's height band. It
scores **nothing**, because it never holds. That is the rule working.

### Gates

To be promoted, a submission must pass **all** of:

- Tier 0 on ≥80% of the public cases.
- Tier 0 on ≥80% of 20 held-out cases.
- Zero deaths on the nominal case.
- A summit for a full-climb claim.

## Submit

```powershell
python -m challenge.evaluate --policy my_policy:MyPolicy --out reports/my_run
```

A policy is any object with `.action(observation) -> (2,)` and an optional
`.reset()`. Submit the policy plus the command that produces your score.

---

## What is hard, honestly

The failure modes we actually measured, so you can avoid re-discovering them:

**Gaussian exploration cannot find the ledge swing.** The critical move is a
coordinated ~120-tick swing. Exploration at σ≈0.09 essentially never samples
it; the demonstrated motion used σ≈0.5. If your policy is a Gaussian around a
constant, it will not get there.

**Coarse control works; fine control does not.** A per-tick trajectory that
reaches and holds the ledge exists. Resampling it to the 4-tick decision
interface fails. The control bandwidth is the problem.

**Demo seeding diluted rather than helped.** Replaying long demonstration
segments whose states no longer match the policy's actual state reduced ledge
arrival. Matched, short, state-consistent imitation is the version worth
trying.

**The reward clock is not the decision clock.** A per-decision discount of 0.99
at 4 ticks/30 Hz gives a 9.2-second half-life. The climb takes minutes. The
default here discounts in *game time* with a 120-second half-life.

## Ideas that are not yet dead

- Residual policies on top of the contact-sign controller.
- Goal-conditioned or hierarchical control, where sub-goals are the tier boxes.
- Curriculum over hand-placed configurations, with honest admission that the
  place is labelled as such.
- Plan search (CEM/MPPI) in the pointer space, which is what found the
  original ledge trajectory.
- Longer-horizon action parameterization to bypass the 4-tick bandwidth limit.

## Baseline to beat

`contact-sign-stroke-controller-v1`, hand-designed, not learned:
holds (322.59, 104), 83 units retained, 0 deaths, passes tier 1.

## License

Source code is MIT. The game assets are third-party and are **not** MIT-licensed.
Read `NOTICE` before redistributing.
