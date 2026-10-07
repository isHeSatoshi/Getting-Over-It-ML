# Accelerated original-game backend

Implemented and tested on 2026-10-03. This is an acceleration of the original
compiled game, **not a reimplementation of its physics**.

## Research decision

The first component benchmark found that collision queries occupied about
87% of browser-side simulation time on a 600-tick clockwise sweep. The
reference game's physics works; the obsolete Node worker's constant-false
collision stub does not.

Rewriting the physics would introduce avoidable model error. The measured
bottleneck instead supports exact reuse of repeated collision queries and
removing transport/display overhead. This produces a usable fast backend now
without inventing friction, gravity, hammer torque, or terrain geometry.

## What changes, and what stays original?

| Component | Fast backend |
|---|---|
| Game blocks, custom physics, controller easing, gravity | Original packaged project |
| Collision implementation and silhouettes | Original real renderer |
| Repeated identical collision query within one synchronous tick | Memoized result of the original renderer |
| Coordinate precision | No rounding, bins, approximate normals, or proxy hitboxes |
| Telemetry variables | Cached references to original variable objects |
| Screen drawing/DOM telemetry display | Suppressed during stepping; explicit `research.render()` available |
| Python/browser connection | Persistent authenticated loopback WebSocket |
| Terrain observation features | Vectorized equivalent of the same alpha-map marching/bisection |
| Reward and episode lifecycle | Unchanged `climb-v2` contract |

### Exact collision reuse

The cache key includes the Player hitbox skin identity, precise position,
scale, direction, visibility, effects, candidate drawable IDs, Level geometry,
and native stage size. Any Level transform/skin/effect mutation invalidates
candidate geometry and cached results. The cache is cleared every tick.

Only original Player body/hammer hitbox queries against the current Level
drawables are cached. Other targets/queries still use the real renderer.
The originals are never replaced with a contact guess. This scope assumes
the project's static costume assets; it is not a general-purpose cache for
arbitrary projects mutating skin pixels synchronously.

On the 600-tick sweep, 24,513 of 29,770 eligible queries reused an identical
result, about 82%. Unit tests require tiny position changes, Level transforms,
skin changes, effects, and tick boundaries to invalidate reuse.

### Transport and ownership

`FastBridge` starts its own isolated Chrome worker and loopback asset/WebSocket
servers. The browser authenticates with a fresh random token and a matching
Origin. The token is not written to artifacts and is removed from browser
history after connection. Servers bind only `127.0.0.1`.

Requests are serial with IDs and timeouts. Remote errors, missing workers, and
out-of-order replies fail explicitly. No action is silently retried after a
timeout, because that could advance physics twice. Closing the worker stops
only resources it owns, never the user's browser or existing profiles.

On this desktop the isolated worker is headed. On a separate non-desktop
training host it is headless by default. The embedded CLI is still available
for reference diagnostics, but is not the fast transport.

## Fidelity gates actually passed

Reference: compiled original game, normal display drawing, no collision memo,
Selenium transport. Fast: compiled original game, display suppression, collision
memo, persistent transport, vectorized features.

Two reset seeds, with different command batch partitioning:

- Idle and downward-push holds.
- 1,200-tick clockwise sweeps.
- Counterclockwise sweeps ending in real death at tick 970.
- 512-tick abrupt random targets.
- 600-tick smooth sweep/hold trajectories.
- Fresh causal-control validation and thirty-reset resource checks.
- Empty-water failure and an upper-gravity placement probe.
- Absolute, velocity, and polar environment steps, including observations,
  reward history, shaping components, terminal flags, and truncation.

All compared raw telemetry fields had **zero measured error**, including
body/hammer positions, finite differences, scripted velocities, angles,
camera/display coordinates, controller memory, collision flags/query counts,
frame IDs, command IDs, and elapsed virtual time.

The two placement cases are deliberately labelled diagnostics. They do not
prove that an agent reached those regions or that all upper-level collision
geometry is covered. Seeds in these tests do not create independent physical
generalization environments.

Closed-loop tests additionally matched policy actions, normalized observations,
rewards, physical progress, and outcomes for:

- Untrained PPO and SAC networks.
- A explicitly labelled constant-push network fixture that transfers real
  contact force and retains 19.21 height units.
- A trusted 128-transition PPO smoke checkpoint, evaluated for 128 decisions
  on both workers.

The fixture is not learned behavior. The smoke checkpoint still retains zero
height. Fidelity success is not policy competence.
The final suite passes 36 Python tests plus the JavaScript memo-invalidation
test. An explicit fast-mode render was also visually checked against the
reference sweep: body `(269.31,32)`, hammer placement, camera-following, and
terrain appearance agree. Rendering does not advance or alter the game state.

## Measured performance, with limits

Paired headed workers on the user's machine:

| Measurement | Reference | Fast |
|---|---:|---:|
| Median browser time, 600-tick sweep | 1,207 ms | 223 ms |
| Approximate sweep throughput | 497 ticks/s | 2,689 ticks/s |
| Median empty RPC | 7.08 ms | 0.30 ms |
| Environment throughput, terrain enabled | 65.9 decisions/s | 103.2 decisions/s |
| Environment throughput, terrain disabled | 90.4 decisions/s | 187.9 decisions/s |

A WebDriver versus WebSocket comparison **on the same fast worker** measured
4.75 versus 0.30 ms median empty RPC. Closed-loop inference tests measured
roughly 2.1–2.6x acceleration. A small 128-transition PPO trial reported about
76 transitions/s including training bookkeeping.

These are bounded local measurements, not capacity guarantees. Timing tails
and machine load vary significantly. Physics-only speedup is about 5.4x in
the paired sweep; end-to-end improvement is smaller because observation and
Python/inference overhead remain.

The first vectorized terrain prototype was slower than the scalar method.
It was revised to avoid per-call tile-key sorting before enabling it.
Descriptor parity is tested at seams and random/world-region points. The
remaining terrain cost is still material; do not claim a 5x learning-throughput
speedup from the physics-only result.

Collision/draw measurements are nested within runtime-step time and must not
be added to it. Draw timing measures CPU submission/waits, not isolated GPU
execution. No parallel-worker scaling or complete-climb throughput was tested.

## Commands

```powershell
python -m pip install -r requirements-research.txt
python -m unittest discover -s tests -p "test_*.py" -v
node tests/collision_memo.test.js
python -m research.fast_fidelity
python -m research.policy_fidelity --decisions 128
python -m research.benchmark --driver selenium --headed
python -m research.benchmark --fast --headed
python -m research.train --backend fast --algorithm ppo --smoke --steps 128
```

Training defaults to `--backend fast`; `--backend reference` remains available.
Before/after training evaluation always uses a separate **reference** worker.
Local smoke caps and the desktop full-training refusal still apply.

For a trusted current trial:

```powershell
python -m research.policy_fidelity --trial "D:\absolute\trial_directory" --decisions 128
python -m research.replay --trial "D:\absolute\trial_directory" --backend reference --driver selenium
```

Both execution modes use the same observation/reward contract. Source and asset
hashes cover all JS helpers and the page entrypoint. Checkpoint evaluation
rejects changed critical source hashes rather than assuming compatibility.

On a **separate training host**:

```bash
python -m research.fast_fidelity --headless
python -m research.train --backend fast --algorithm sac --action absolute --reward-profile settled --remote-training --steps 100000 --seed 0
```

Do not run the second command on the user's desktop or waive failed preflight
checks. This implementation has no full-training result.

## Evidence

Generated artifacts are local and excluded from Git:

- Baseline: `artifacts/benchmark_20261003T173856347145Z/report.json`
- Golden traces: `artifacts/fast_fidelity_20261003T175125550580Z/report.json`
- Closed-loop fixtures: `artifacts/policy_fidelity_20261003T175518367578Z/report.json`
- Fast smoke trial: `artifacts/trial_20261003T175640765838Z/`
- Saved-policy transfer: `artifacts/policy_fidelity_20261003T175800040917Z/report.json`
- Paired benchmark: `artifacts/paired_benchmark_20261003T180035081350Z/report.json`
- Visual check: `artifacts/fast_visual_20261003T180309125271Z/rendered.png`

## Remaining work

Remote training/evaluation, sustained obstacle progress, full-climb fidelity,
upper-level contact coverage, actual summit completion, and robustness to
physical/controller perturbations remain open. Profile the remote host before
adding parallel workers or a native physics port. The present evidence supports
this exact-runtime acceleration, not an arbitrary custom FastSim.
