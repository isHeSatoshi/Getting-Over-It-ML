# Climb reward v2

Implemented in `research/reward.py`, integrated in `research/env.py` and
`research/train.py`. This is a **testable research reward**, not a claim that
it has trained a competent climber.

## Control/telemetry readiness

The observation-action-physics-observation loop is implemented and experimentally
verified near the starting terrain. The current interface additionally checks
clock increments, delivered pointer values, physical finite differences,
world/camera transforms, outcome flags, command IDs, and trace length on each
transition. Bad telemetry raises an error instead of becoming training data.

Three action modes, resets, collision-query telemetry, and Gymnasium lifecycle
have been exercised against the original scripts and real renderer. Contact
flags identify hitbox collision queries; they are **not forces, normals, or
proof of a fixed ledge grasp**. Full-climb physics, upper-level gravity, and
the actual summit sequence remain unverified. There is no claim that all
hidden VM state is in the observation.

## What was wrong with the initial reward?

The first replacement fixed the fake physics but retained a generic
decision discount of 0.99. At four ticks per decision and 30 Hz, the discount
half-life was only **9.20 game seconds**, with an effective discounted horizon
of about **13.33 seconds**. A long climb's terminal outcome becomes almost
irrelevant before the learner even reaches it.

Height-only potential also gives the same local shaping credit to a height
whether it is retained on terrain or briefly crossed in a jump. It should be
an ablation, not an unquestioned sole descriptor. Conversely, paying a
recurring contact/hold bonus would invite camping.

Finally, dynamically normalizing and clipping rewards would mean that a
mathematically policy-invariant shaping formula is no longer the exact
fixed-scale objective delivered to the optimizer. V2 normalizes observations
only, not rewards. Raw reward components remain available in traces.

## Task objective

Every profile shares the same task:

$$
r_t^{\mathrm{task}} =
100\,\mathbf{1}_{\mathrm{success}}
-5\,\mathbf{1}_{\mathrm{death}}
-0.005\,\Delta t.
$$

- Success: the original game's condition `PLAYER Y > 16000`.
- Death: the original game's condition `PLAYER Y < -180`.
- Time: actual simulated ticks divided by 30, not wall-clock time.
- No reward for mouse motion, hammer rotation, contacts alone, episode highs,
  terrain-ray predictions, or resets.
- No stall-based termination. A time limit is a truncation with bootstrap,
  not a fake death.

The clock cost deliberately favors faster completion, but is small enough
that suicide is not preferred merely to escape it. At the default discount,
indefinite idling costs about 0.866 units in discounted return, below the
5-unit death penalty. The configuration checks this bound for all supported
action-repeat lengths. This is a reward-scale sanity check, **not** a promise
that optimal policies never avoid difficult exploration.

## Discount specified in game time

With physics rate $f$, action repeat $k$, and half-life $H$:

$$
\gamma = 2^{-k/(fH)}.
$$

Default: $f=30$, $k=4$, $H=120$ seconds, hence
$\gamma=0.9992301329658564$. This is supplied explicitly to:

1. the potential-shaping formula;
2. PPO or SAC;
3. `VecNormalize` and its persisted state;
4. evaluation.

Evaluation rejects disagreement. Changing action repeat through the environment
API changes gamma to retain the same physical-time half-life. Nonterminal
steps must have the full configured repeat. A terminal event may stop the
last repeat early; SB3 uses the same decision-level gamma and does not
bootstrap that transition. The final outcome's sub-decision timing is not
modeled by a variable-duration discount.

120 seconds is an explicit initial hypothesis, not a tuned optimum. Remote
ablations should include 60 and 240 seconds. A longer gamma does not by itself
solve exploration, critic estimation, or PPO's GAE trace-length limitations.

## Potential shaping

$$
r_t = r_t^{\mathrm{task}} +
       \gamma\Phi(z_{t+1})-\Phi(z_t).
$$

$z$ includes the physical descriptor and observed rolling reward history.
All true terminal states have $\Phi=0$. A truncation keeps the actual final
potential and must bootstrap. Resetting the environment produces no reward.

The bounded height transform is:

$$
g=\max(0,Y-Y_{\mathrm{spawn}}), \qquad
P(g)=4\,\frac{\log(1+\min(g,D)/100)}{\log(1+D/100)},
\quad D=16000-Y_{\mathrm{spawn}}.
$$

Log compression supplies useful variation early in the climb while retaining
a nonzero gradient beyond the first 400 units. A naive `min(4,g/100)` would
stop changing above 400 units. The potential stays in $[0,4]$, well below
the success payout. Below-spawn waiting does not have a negative potential
from which discounted shaping could produce positive per-step payments.

### Three profiles, identical observations

| Profile | Potential | Purpose |
|---|---|---|
| `sparse` | 0 | Honest unshaped task baseline |
| `height` | $P(g)$ | Height-only shaping ablation |
| `settled` | $0.25P(g)+0.75P(g_{\mathrm{settled}})$ | Default experimental shaping |

The sparse profile still observes the same history/features. This isolates
reward choice rather than changing the policy's information at the same time.

### Settled-height descriptor

For the last 30 physics ticks (one second):

1. Retain each tick's nonnegative body height gain.
2. Mark a tick qualified only if a real body or hammer collision query hit,
   and body displacement speed is at most 2 units/tick (60 units/second).
3. Require at least 80% qualified ticks.
4. If qualified, use the **minimum** height gain over the whole window.
   Otherwise settled gain is zero.

History starts at zero after every reset. This prevents an initial airborne
spike from certifying progress before a full window exists. Falling or losing
support reduces the descriptor. It is not a high-water mark and is not paid
again for every tick held.

This is a conservative **proxy for retained progress**, not perfect contact
mechanics. Slow motion along a wall can qualify; ledge geometry/force is not
inferred. The 25% height term still provides an exploration signal during
launches. Window, support fraction, speed threshold, and mixture are explicit
hyperparameters requiring remote ablation.

The complete 30-sample gain and qualification histories are in the observation,
along with potential descriptors and qualification fraction. Otherwise the
reward would depend on hidden window contents. The v2 default observation is
89 elements without terrain, or 217 with terrain (26 original features +
63 history/descriptor features + 128 terrain features). Old policies and
normalizers are incompatible and are rejected, not silently reshaped.

## Why this cannot pay repeated jump/contact exploits

For any $N$ transitions using the same gamma:

$$
\sum_{t=0}^{N-1}\gamma^t
 \left(\gamma\Phi(z_{t+1})-\Phi(z_t)\right)
 =-\Phi(z_0)+\gamma^N\Phi(z_N).
$$

Thus:

- a cycle returning to zero potential cannot earn discounted shaping;
- a completed success/failure episode cancels all shaping;
- a stationary positive-height plateau gets negative discount leakage,
  not a recurring hold bonus;
- switching contact flags without height cannot create potential at spawn;
- failure zeroes potential rather than paying for the measured negative height;
- an incomplete/truncated rollout still has a potential boundary term.

**Do not compare summed shaped rewards from incomplete episodes as task
success.** Sparse task return, retained physical height, falls, and actual
completion remain the evaluation criteria. The three profiles preserve the
same discounted task objective on fully terminated episodes. The guarantee
assumes proper bootstrapping, a fixed configuration, and an adequate state
representation; function approximation and partial physical observability
still affect learning.

## Validation performed

29 focused unit contracts currently pass. They include idle camping,
below-spawn waiting, contact-only behavior, ballistic/fast-contact rejection,
rolling-minimum regression, repeated jump/fall cycles, continued high-altitude
gradient, failure/success potential cancellation, time limits, invalid
telemetry, history observability, clock mismatch, and configuration sanity.

`python -m research.reward_audit` also runs fresh causal-control checks and
scores identical real-game traces with all profiles. It verifies exact
online/offline reward agreement and unchanged physics across profiles.

Measured examples, discounted shaped return over the bounded trace:

| Real trajectory | Retained height | Sparse | Height | Settled |
|---|---:|---:|---:|---:|
| Idle, 6 seconds | 0 | -0.02950 | -0.02950 | -0.02950 |
| Downward target held, 6 seconds | 19.21 | -0.02950 | 0.10418 | 0.10418 |
| Random targets, 8 seconds | 25.69, not settled | -0.03910 | 0.13281 | 0.00387 |
| Smooth sweep plus hold, 16 seconds | 28.00 | -0.07644 | 0.10077 | 0.10077 |

The random trace's peak gain was 164.97, but its final settled gain was zero.
The reduced settled-profile credit is an intended descriptor difference,
**not evidence that this profile trains better**. Durations differ across
rows, so this table is not an algorithm-performance ranking.

Evidence: `artifacts/reward_audit_20261003T170609011413Z/report.json`.
The audit includes a deliberately placed empty-water failure test whose
discounted episode return is the same across all profiles.

Small PPO/SAC smoke checks exercise optimizer integration only. They do not
establish learning; their deterministic outcomes do not improve reproducibly.
No full training is run locally.
The final raw-reward checks used 128 CPU transitions each:
`artifacts/trial_20261003T171459608866Z/` (PPO) and
`artifacts/trial_20261003T171215291202Z/` (SAC).

## Reproduce and compare

```powershell
python -m unittest discover -s tests -p "test_research*.py" -v
python -m research.reward_audit
python -m research.train --algorithm sac --action velocity --reward-profile settled --smoke --steps 128
```

On a separate training host, hold the algorithm, action mode, observations,
seeds, normalization, and transition budget fixed while changing **only**
`--reward-profile`. Then ablate the physical-time discount. Record all
components, configurations, raw physical progress, and held-out evaluations.
Never interpret a bigger shaped return as proof that one profile is better.

## Sources and limits

- Ng, Harada, Russell (1999), policy invariance under reward transformations:
  <https://www.cs.utexas.edu/~shivaram/readings/b2hd-NgHR1999.html>
- Grzes (2017), terminal-state handling in episodic reward shaping:
  <https://www.cs.kent.ac.uk/people/staff/mg483/documents/grzes17goals-in-pbrs.pdf>
- Continuous-time discounting supplies the exponential-time parameterization;
  the numerical choice of half-life and settled-height proxy are project
  hypotheses, not conclusions borrowed from a paper.

Reward shaping cannot replace a reach-and-hold curriculum, goal-conditioned
replay, or systematic exploration if the global sparse objective remains
unlearnable at the available budget. Those are separate experiments, not
hidden reward changes.
