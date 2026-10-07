# RL-Over-It: physics/interface audit and research baseline

Audit date: 2026-10-03. No full training was run locally. This is a validated
research starting point, **not a demonstrated solution to the climb**.
The subsequent exact-runtime acceleration and measured fidelity results are
documented in `FAST_BACKEND.md`; a separate approximate simulator was not built.

## Main finding

The dominant failure is not the choice of PPO versus SAC. The legacy Node
worker substitutes a renderer whose `isTouchingDrawables()` always returns
false. The actual Player physics repeatedly calls `sensing_touchingobject(Level)`
using both its **player hitbox** and **hammer hitbox** costumes. Scratch routes
that block through the renderer. Consequently:

1. The player falls through the starting terrain.
2. Moving the hammer cannot transfer force through terrain contact.
3. The game loop/legacy recovery path repeatedly restarts the fall.
4. False contact telemetry and restart-induced height changes look like reward.
5. The learner fits this broken process, not Getting Over It.

The old specification explicitly asserted that a renderer was unnecessary.
That is false for this game. Running many steps of the wrong dynamics faster
does not yield a useful simulator.

### Matched-action evidence

Same 180-tick, radius-90 clockwise pointer trajectory:

| Measurement | Legacy Node | Real game renderer |
|---|---:|---:|
| Reset world Y | -262.4000 | 21 |
| Body X excursion | 0 | 269.3061 |
| Maximum world Y | 98.7000 | 53.9250 |
| Frame-counter regressions | 4 | 0 |
| Legacy claimed contact frames | 180/180 | Not used |

The legacy maximum is caused by restarting at Y=100, not climbing. The
existing `env_8001.log` independently shows recurrent highs of 98.7 and
repeating altitude sequences despite changing policy actions. We did not
verify the user's reported TensorBoard explained-variance value; that metric
would not validate the environment in any event.

The downloaded `project.json` matches the project inside the provided zip.
Its SHA-256 is
`e72f65668b86b0e37c30c2f2c67f2a39319acb1a31f5fe589bd5842e2c94e120`.
This proves local asset identity, not independent authentication of the
Scratch website's current project version.

## Mechanics traced from the original project

`python tools/inspect_project.py Player Level Hammer` prints original block IDs.
These IDs are better audit anchors than line numbers in the single-line JSON.

- Player `bF`/`bG`: commanded hammer displacement is 0.4 times the error between
  the mouse reporter and the hammer's offset from `PLAYER + (cox,coy)`.
  `cox=0`, `coy=20` at initialization.
- Player `I`/`J`: changes in that displacement are limited to magnitude 40.
- Player `K`: displacement is capped at magnitude 50.
- Player `L`: the hammer/body separation is constrained by `MIN LEN=26` and
  `MAX LEN=102`. These are custom scripted constraints, not a standard
  torque-controlled rigid-body joint.
- Player `iL`, `b(`, `b-`: hitbox costume collisions against Level determine
  hammer contact and body contact.
- Player `ch`/`ci`: `touch x/y` hold a decaying **control error memory** when
  hammer contact occurs. They are not world contact coordinates.
- Player `lM`/`lN`: a new game initializes body position to `(0,100)`, then it
  falls and settles at `(0,21)` with valid collisions.
- Player `an`/`ao`: the gameplay conditions are `Y > 16000` for success and
  `Y < -180` for failure. A large negative delta is not itself a death event.
- Player `mc` through `mg`: ordered broadcasts handle camera placement,
  collision correction, hammer, player physics, and level positioning.
- Level `fn`: tile centers are `(464*lx,344*ly) - CAMERA`. PNG costumes have
  bitmap resolution 2, and adjacent tiles overlap.
- Player `d@`: the original in-game timer uses `FRAME/30`.
- Gravity changes in the upper level, including a planetary region. Retaining
  the game scripts avoids silently replacing these mechanics with constant gravity.

The rendered Hammer direction is a **visual orientation**, not necessarily the
angle of the physical hammer/body vector. `atan2(HY-PY,HX-PX)` supplies that
angle directly. The Player sprite switches costumes and positions during
collision probes, so sprite motion alone is not an adequate physics state.

## Which previous explanations were supported?

| Hypothesis | Finding |
|---|---|
| Current mouse commands are disconnected | Disproved for the current Node worker: it already calls `postData`, and hammer coordinates respond. |
| Scratch always ignores direct `_scratchX` changes | Disproved: the installed Scratch mouse getter reads it; the browser reporter also returned an injected value of 77. `postData` remains the proper supported interface. |
| Y=21 is an intro screen and -264.7 is the starting rock | Disproved: real collisions hold the visible player at Y=21; -264.7 occurs in the broken falling process. |
| Cartesian targets inherently cannot work | Disproved as a categorical claim: a constant downward target lifts the body through contact. Abrupt targets may still be a worse exploration parameterization. |
| A held click is required for gripping | Disproved for these physics scripts: held/released trajectories match. Button sensing is used elsewhere, such as menus. |
| Long training can fit useless behavior | Supported: body X is action-insensitive in the old backend; its losses cannot establish gameplay competence. |

## Other defects found

- Node contact is inferred from nonzero `touch x/y`, including tiny decayed
  remnants, and its normal is hard-coded to `(0,1)`.
- Node finite differences depend on how many steps occurred between telemetry
  packets, but they are reported without that interval.
- Old effort is clipped to `[0,1]` even though the game uses thresholds such
  as 5, 10, and 17.
- The old environment forcibly substitutes -264.7 for a measured reset above
  -200. It mixes a fabricated reward baseline with a different observation.
- The old terrain cache is computed before acting and reused for the next
  observation, creating stale terrain features.
- Rays and ledge offsets are unnormalized beside small scaled state features.
  Numerous constant/dummy features further complicate the 200-element vector.
- The old reward mixes a per-frame gamma with decision-level discounting,
  high-water bonuses, contact bonuses, and unvalidated alignment rewards.
  Its configured fall threshold is not the threshold actually used.
- The browser live-action poller continuously reads a file and sets the
  always-running flag. This races explicit commands. Independent real-time
  browsers cannot reproduce a fast Node trajectory merely by polling its
  latest action; states, timing, physics, and resets must also agree.
- The original tests check frame advancement, tensor shape, and reward math.
  They even accept Y=21 while other code asserts that is an intro screen.
  None requires the hammer to transmit force to the body.
- A first new reset implementation reloaded all project assets every episode.
  After about two dozen resets the isolated Chrome tab crashed. Restoring
  initial state in place removes repeated costume loads. Thirty-reset
  regression tests now show stable counts: 27 targets and 281 skins.

The old trainer and default environment are disabled. The old implementation
remains available for forensic comparison; old checkpoints are not resumed.
The old streamer/evaluator also stop before creating browser/server resources.

## Current architecture and its guarantees

`research/runtime.js` executes the provided packaged TurboWarp VM with its
**actual renderer and original game blocks**. There is no cloud provider,
action-file polling, automatic keyboard recovery, or autonomous stepping
interval. Input goes through the mouse device before each explicit `_step()`.
The default reference stage is 480x360 at 30 ticks/second.

Telemetry contains world coordinates, camera/display coordinates, physical
vector angles, per-tick finite differences, separate scripted impulse
velocities, and labeled control memory. Collision instrumentation records
whether the actual renderer returned a hit for each hitbox during the tick.
These are **collision-query events**, not forces, normals, or persistent
support contacts; no unavailable quantity is invented.

Resets stop threads and delete clones through the VM, restore original
variables/list values and sprite transforms, broadcast New Game, and advance
120 ticks. Variables are restored in place to preserve compiled references.
Starting terrain support must be measured, not substituted.

Gymnasium rejects invalid observations, stale frame counters, mismatched
command acknowledgements, and unsupported backends. It requires reset after
termination. A death cuts off the action-repeat loop without auto-respawning.
The v2 observation contains 26 physical/controller features, 63 reward-history
features, and optionally 128 scaled terrain-ray features. It is a useful state descriptor, **not a
claim that every hidden Scratch scheduler variable is observed**.

Three action parameterizations permit controlled ablations:

- Absolute player-relative mouse offsets in `[-128,128]^2`.
- Integrated pointer velocity, at most 8 units per tick per axis.
- Integrated polar angle/radius, with the game's body-offset convention.

The original controller handles easing in all modes. No macro has privileged
access to body position or force during training.

The initial replacement reward was subsequently revised after a separate
research audit. The current `climb-v2` contract is in `REWARD_DESIGN.md`:
success +100, death -5, time cost 0.005/game-second, and bounded
potential shaping with sparse/height/settled profiles. The shared physical-time
discount has a 120-second half-life. Terminal potential is zero; truncation
bootstraps. All rolling reward history is observable. Observation normalization
is saved/frozen; rewards are not dynamically normalized or clipped.
There are no paid contact, guessed-hook, or restart-high bonuses.

The terrain descriptor reuses the working asset loader, but samples the union
of overlapping tiles. It is not used to replace game collision physics.
135 points near spawn yielded 134 agreements with a real-renderer 1x1 hitbox.
The mismatch at `(-80,-30)` is retained, not hidden; a hitbox footprint and
point-alpha test can disagree at boundaries.

## Bounded experimental results

### Causal state/action tests

- Idle: stable body Y=21 over 60 ticks.
- Right/left targets: relative hammer X approaches +90/-90.
- Up target: hammer/body vertical separation approaches 97.50.
- Down target: body rises 19.21 units with hammer terrain hits.
- Clockwise sweep: body reaches X=141.49 in 120 ticks; camera X changes by 139.
- One uninterrupted batch and batches of seven produce identical physical traces.
- Mouse held/released produces identical traces.
- Game frame, tick, command ID, 30 Hz virtual time, finite differences, and
  world-to-camera relations are checked every tick.
- An explicitly labeled diagnostic placement above empty water reaches
  Y=-187.37 and terminates after 17 ticks. This is a failure-event test, not
  evidence of learned gameplay.
- Compiled versus interpreted execution matches exactly on the 180-tick
  sweep. The old packaged 640x480/60 Hz settings give the same **per-tick**
  trajectory in this test, but have a different time interpretation.

These checks establish the important early-game loop. They do **not** prove
equivalence at every surface, altitude, or timer-dependent event.
The Gymnasium environment checker also passes. It warns about the deliberately
unbounded observation Box; finite telemetry is separately enforced, and
normalization handles observation scaling. The later reward audit expanded
coverage to 29 unit contracts and per-transition telemetry consistency checks.

### Control and ML baselines

The neural trials below used the **initial v1 reward/observations**, not the
later `climb-v2` reward. They cannot be treated as current-reward results.

| Method | Local budget | Physical outcome |
|---|---|---|
| CEM, smooth absolute-pointer knots | 8 candidates x 3 iterations x 360 ticks | Final X=444.50; maximum gain 143.53; retained gain 34.00 |
| Same CEM trajectory, 120-tick final-pointer hold | No learning | Retained gain remains 34.00 |
| PPO, absolute actions | 512 CPU transitions | Stochastic rollout reached +195.31 transient gain; deterministic before/after evaluation retained 0 |
| SAC, velocity actions | 512 CPU transitions | Pipeline completed; deterministic before/after evaluation retained 0 |

The CEM replay was identical for seeds 1001–1003. Physical gameplay in the
tested region is effectively deterministic; those seeds are **not three
independent generalization environments**. CEM is a bounded open-loop search
baseline, not a reactive learned player. Its retained 34-unit gain is about
0.21% of the starting-to-summit altitude difference.

The neural trials establish valid transitions, optimizer execution, physical
monitoring, normalization/checkpoint saving, and evaluation. They do not
establish learning, do not rank PPO against SAC, and do not justify a paper
claim of solving the game. The two trials also use different action spaces,
so treating their outcomes as an algorithm comparison would be invalid.

### Local evidence directories

Generated files are intentionally excluded from Git; rerun the documented
commands to regenerate them. During this audit:

- `artifacts/fidelity_20261003T155952014147Z/evidence.json`
- `artifacts/validation_20261003T155839075343Z/evidence.json`
- `artifacts/search_20261003T160016867709Z/search.json`
- `artifacts/replay_20261003T160331691620Z/evidence.json`
- `artifacts/trial_20261003T160108989112Z/` (PPO)
- `artifacts/trial_20261003T160420419247Z/` (SAC)

The latest trial records source hashes, all-asset and runtime hashes, actual
dependency versions, configuration, and dirty-worktree status. Early audit
runs predate some of that instrumentation. Raw diagnostics preserve actions
and per-tick state rather than just aggregate reward.

## Why this architecture, and what algorithm next?

| Approach | Fit to discovered mechanics | Decision |
|---|---|---|
| PPO | Simple, stable baseline; on-policy sampling and difficult sustained exploration can be expensive | Keep as a comparison, not the assumed answer |
| SAC | Low-dimensional continuous control; replay reuse and entropy help sample efficiency | Keep as an equal-budget off-policy comparison |
| Recurrent policy / history | Can help unobserved control/scheduler memory; cannot fix false physics | Test only after explicit-memory observations work |
| Goal-conditioned SAC + HER | Nearby reachable ledges create short tasks; failed attempts provide achieved goals | Strong follow-up if global progress stalls; requires honest reach/hold predicates |
| Hierarchical skills | Useful once placement, pushing, pulling, and hooking skills are demonstrated | Do not hand-design a hierarchy before measuring primitive success |
| Exact-runtime CEM/MPC | Real dynamics avoid model bias; good local control baseline | Reset/replay works now; arbitrary incomplete VM snapshots are not safe planning states |
| Go-Explore-style archive | Determinism allows replay back to a reached state before exploring further | Promising for long-horizon exploration; later robustify to feedback control |
| Learned-model MPC / TD-MPC2 | Could amortize planning; collision transitions create difficult model-error regimes | Defer until contact-stratified prediction/rollout error is measurable |
| Custom FastSim | Would need exact silhouette collisions, constraint/contact correction, controller memory, scheduling, and gravity regimes | Not justified by current evidence |

**The first fast execution target is the original compiled game, not new
physics.** Batched real-game diagnostics already ran hundreds of ticks in
fractions of a second. The local embedded ML trial achieved about 27 decisions
per second because per-decision browser RPC and Python features dominate.
These are different measurements. No multiworker scaling claim is made.

Implementing a native simulator is justified only if profiling on the remote
host shows that original-runtime execution, rather than RPC/reset/feature
overhead, limits experiments. Any replacement must pass action-sequence and
contact-stratified fidelity gates, including fall/summit outcomes. One-step
average position error is insufficient for contact-rich long-horizon transfer.

### Literature grounding

- Schulman et al., **Proximal Policy Optimization Algorithms** (2017):
  <https://arxiv.org/abs/1707.06347>
- Haarnoja et al., **Soft Actor-Critic** (2018):
  <https://arxiv.org/abs/1801.01290>
- Andrychowicz et al., **Hindsight Experience Replay** (2017):
  <https://arxiv.org/abs/1707.01495>
- Ecoffet et al., **First return, then explore** (2021):
  <https://www.nature.com/articles/s41586-020-03157-9>
- Hansen et al., **TD-MPC2: Scalable, Robust World Models for Continuous Control**
  (2024): <https://arxiv.org/abs/2310.16828>
- Ng, Harada, Russell, **Policy invariance under reward transformations** (1999):
  <https://www.cs.utexas.edu/~shivaram/readings/b2hd-NgHR1999.html>

These support algorithm families and evaluation principles, not a claim that
any one paper's method has been proven appropriate for this particular game.

## Remaining gates before serious training/publication

1. Compare replay against an unmodified reference browser at multiple
   contact geometries and at mid/upper-level gravity regimes. Validate the
   actual summit/win event, not only a synthetic unit state.
2. Run the equal-budget remote matrix described in `REMOTE_TRAINING.md`.
   Require physical retained-height and reach-and-hold improvement, not reward.
3. Evaluate perturbations to start/controller state and feedback recovery.
   Cosmetic random seeds are not a robustness test.
4. If progress plateaus, implement and compare achieved-goal replay,
   exploration archives, and trajectory-to-policy distillation. Do not
   silently change rewards/curricula within a reported experiment.
5. Profile browser RPC, real collision queries, and terrain features before
   building a replacement simulator or claiming throughput/scaling.
6. Resolve game attribution, redistribution, project version provenance,
   and the repository's missing license before open-source/paper release.

There is no trained competent climber, full-climb success, or completed
research study in this repository yet. The useful accomplishment is replacing
untrustworthy training with a measured, reproducible physical interface.
