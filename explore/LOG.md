# explore/ experiment log (bounded, cheap, verified steps)

Every entry: command, budget, result. Machine: 4 CPU, 7 GB RAM, no GPU, Chrome 154 headless,
Python 3.12 venv at `.venv` (`pip install -r requirements-research.txt huggingface_hub httpx`).
Env for all commands: `cd <repo> && . .venv/bin/activate && export RL_CHROME_NO_SANDBOX=1 PYTHONPATH=$PWD`.

## E0 harness validation (2026-10-07)
- `python -m unittest discover -s tests -p "test_*.py"`: first run 506 tests, 16 errors, all
  `ModuleNotFoundError` for `huggingface_hub`/`httpx` (remote-deploy code, unrelated to physics).
  After `pip install huggingface_hub httpx`: **511 tests OK**. `node tests/collision_memo.test.js`: OK.
- Headless real game: startup 5.5 s, reset state `(0, 21)`, as documented.

## E1 VM structure probe (budget: 2 runs, ~10 s each)
- Commands: `python explore/probe_vm.py`, `python explore/probe_vm2.py`.
- At every tick boundary: exactly 1 live thread (Player main loop, compiled, stack depth 1);
  27 targets, constant over a 1200-tick sweep (no clone creation/deletion); no edge-hat state;
  lists are tiny (<= 76 items). All game state is in variables/lists/sprite props.

## E2 exact snapshot/restore (budget: 1 run, ~1 min)
- Change: additive `snapshot/restore/dropSnapshot` in `research/runtime.js`, RPCs in
  `research/fast_rpc.js`, `FastBridge.snapshot/restore/drop_snapshot`. Physics untouched.
- Command: `python explore/snapshot_fidelity.py` (result: `explore/snapshot_fidelity_result.json`).
- Test: 4 prefix paths x 5 snapshot ticks x 2 continuations = 40 cases, 300-tick continuations,
  200-tick divergence between runs. Straight run vs restore-after-drift vs second restore compared
  on **every telemetry field of every tick** (zero tolerance).
- Result: **40/40 exact, 0 mismatches**; 200-300 contact ticks per case; includes a death state.
  Snapshot 1.3 ms, restore 1.0 ms (vs O(prefix) replay).
- Scope limit: tested only in the spawn region (|X|<900, Y<100). Must be re-verified at new
  heights/regions before trusting restores there (script is reusable with a different prefix).

## E2b throughput on this box (budget: ~1.5 min)
- Command: `python explore/bench_one.py <secs> <chunk> <tag>` (restore + step chunk, random target).
- 1 worker: 1151 ticks/s (chunk 8), 1931 (chunk 32), 2284 (chunk 128). Per-call overhead ~3.7 ms,
  mostly JSON of the 43-field per-tick trace.
- 4 parallel workers (chunk 32): 1797-1867 ticks/s each, ~7.3k ticks/s total (near-linear on 4 CPUs).
- Added page-side `exploreSegment`/`seedCell` (runtime.js) so Go-Explore needs ~1 RPC per segment.

## E3 Go-Explore smoke: 60 s, 1 worker, seed 0
- Change: `explore/goexplore.py`; search at the policy interface (pointer offset in [-128,128]^2
  held 4 ticks/decision); cell = (floor(x/16), floor(y/8)); keep fewest-tick entry per cell;
  select by novelty (chosen^-0.5), half the time restricted to top 10% by Y.
- Command: `python explore/goexplore.py --secs 60 --seed 0 --out explore/runs/e3_smoke`
- Result (explore/runs/e3_smoke/summary.json): 1280 cells, 1148 segments, 82,556 ticks (1373 ticks/s).
  First-ledge box (X 305-335, Y 100-112) *visited* at 7.4 s (visit, not a verified hold).
  **maxY 352.8** (previous learned best ~100) at X~1091; max X with Y>=90: 1408.
- Independent check: best path (109 decisions) replayed from a **fresh reset with straight stepping,
  no snapshots**: final body (1091.0257564332799, 352.76605815747035), tick 556, exact match.
- Caveat: cell registration is by body position at a decision boundary, so transient/airborne
  states count. Retention/hold of any found state is not yet tested.

## E4 four independent seeds, 300 s each (first launch invalid, second valid)
- First launch used `nohup ... &` inside one shell call: processes were killed when the call returned
  (empty logs, no results). Not a search result. Relaunched with the tool's background mode.
- Command (per seed s=1..4): `python explore/goexplore.py --secs 300 --seed $s --out explore/runs/e4_seed$s`
- Result: maxY(any) 928 / 1189 / 1251 / 1246 (seeds 4/2/3/1), maxX(y>=90) up to 2777, 3.6k-4.1k cells,
  ~1.1-1.2k ticks/s each. All four best paths replay **exactly** from a fresh reset (match=True).
- **Finding (invalidates the headline number):** `explore/inspect_path.py` on seed 3's best path shows
  the body flung at up to 40 units/tick, in mid-air at the end (screenshot
  `explore/runs/e4_seed3_best.png`). Holding the last pointer for 180 ticks drops it from Y=1251 to
  Y=643. These are transient apex states, not retained progress. My "top 10% by Y" selection was
  chasing exactly the transient height the brief warns about. Reporting these Y values as progress
  would be wrong.

## E5 retained-state search, 90 s, 1 worker, seed 0
- Change: in-page **hold test** (research/runtime.js `holdTest`): for states with speed < 8 and
  Y within 60 of the retained frontier, freeze the last pointer for 90 ticks, require
  dY > -6 and |dX| < 12 and alive, then roll back. Cells keyed with a `|R` suffix when retained.
  Exploit-mode selection only among retained cells, weighted exp((y - maxRetainedY)/40).
- Command: `python explore/goexplore.py --secs 90 --seed 0 --out explore/runs/e5_smoke`
- Result (explore/runs/e5_smoke/summary.json): **maxRetainedY 328.4 at X 844.2**; 323 retained cells;
  retained state inside the first-ledge box found at 21.9 s; maxY(any) 439; 2075 ticks/s.
- Independent verification (fresh reset + straight replay, no snapshots): final body
  (844.1828059935341, 328.37562404909835), tick 720, exact match; after a further 180-tick hold of
  the last pointer: (842.90, 326.06), min Y 325.56 -> **held = True**.
- Compare: six RL campaigns (~28 CPU-hours) best learned reach Y 96 at X 279, 0 first-ledge holds.

## E6 four islands with migration, 600 s each (seeds 11-14), `--max-cells 20000`
- Command (per seed s=11..14): `python explore/goexplore.py --secs 600 --seed $s --max-cells 20000 --share-dir explore/runs/e6_share --out explore/runs/e6_seed$s`
  Islands publish their best retained path to the share dir every 20 s and import a better foreign
  one (margin 30) by root-snapshot restore + straight replay.
- Retained-Y curve (seed 14): ~170 @20 s, 1.4k-1.7k @227 s, 3.3k-3.7k @424 s, **3993 @600 s**.
- Final, each verified by **fresh reset + straight replay, then a 180-tick hold** (match = exact):
  seed 11: retained Y 3840.0 (X 2514.7), tick 4704, held; seed 12: 3829.9 (X 2419.4), tick 4848, held;
  seed 14: 3993.1 (X 2826.3), tick 5064, held (min Y during hold 3993.9). 7-8 imports each.
- Seed 13: **infrastructure failure at ~500 s** - Chrome renderer OOM-killed by the memory cgroup
  (limit 7.09 GB; four renderers ~1 GB each + GPU procs). Last published best 3820.5. Not a search result.
- Cause: ~80 KB per stored snapshot (boxed [var,value] pairs). Fix: packed typed-array snapshots
  (no `previous`), re-verified with `python explore/snapshot_fidelity.py`: **40/40 exact again**
  (snapshot 1.2 ms, restore 1.1 ms). Added `--heap-mb` pruning guard and `--stall-s` stop rule.
- Caveat: retained = 90-tick hold of the last pointer (dY > -6, |dX| < 12). Upper regions with
  different gravity may need a different criterion; revisit if progress stalls.

## E7 four islands, seeds 21-24, start from E6 bests, `--secs 900 --stall-s 300 --heap-mb 500 --max-cells 12000`
- Command (per seed s=21..24): `python explore/goexplore.py --secs 900 --stall-s 300 --heap-mb 500 --max-cells 12000 --seed $s --share-dir explore/runs/e7_share --out explore/runs/e7_seed$s`
  (e7_share initialised with copies of E6's best_11..14.json).
- Curve: ~4000 plateau for ~2.5 min, then 5050 by ~360 s, then **plateau at ~5054** for 5+ min; seeds 21/24/22
  stopped on the stall rule; each best verified by fresh replay + 180-tick hold (match True, held True):
  seed 21: 5053.6 (X 1507), seed 22: 5054.3 (X 1511), seed 24: 5053.7 (X 1535). maxY(any) <= 5108.
- Diagnosis of the 5054 plateau (`explore/inspect_path.py`, `explore/terrain_map.py`, real-renderer terrain probe):
  body stands on the tip of a small structure (hammer on it at ~Y 4952); open space around; the next
  solid terrain seen is a block ~500 units to the right and ~120-270 higher (X~1990-2110, Y~5170-5330).
  Not climbable by reach (hammer ~100 units): needs a launch/fling across a gap. Even transient height
  tops out at 5108, so this is a physical gap, not a hold-criterion artifact.
- Route sanity (seed 22 path, 6256 ticks = ~3.5 game-min): body/hammer contact on most sampled ticks,
  X wanders 800 -> 3500 -> 1500, peak speed 81 units/tick during short launch events.
- Next change (E8): retained cells also keyed by hammer sector (8) x near/far; when stalled > 90 s use 80%
  retained-frontier picks and 2x segment length; islands import a random near-best path (diversity);
  `explore/run_islands.py` supervisor runs bounded rounds with fresh browsers (memory) and stops on
  success or 3 rounds with < 25 gain.

## E8-E10 plateau at retained Y ~5054-5056 (about 45 min of 4-island time, no gain)
- E8 round 0 (supervisor, hammer-sector retained cells, adaptive 80% frontier picks after 90 s stall, random near-best
  imports): `python explore/run_islands.py --share-dir explore/runs/e8_share --rounds 6 --round-secs 420 --base-seed 100`
  stopped after round 0: global best 5054.85 (previous 5054.3). maxY(any) 5116. Killed rounds 1-5 (flat).
- E9 (route-aware import: replay from root snapshot, hold-test every 12 decisions, register branch points;
  3-tier selection): 4 islands, killed at 186 s of 420 s: best retained 5055.8; flat.
- E10 CEM from the frontier state (`explore/cem_launch.py`, goal box X 1960-2110, Y 5170-5330 from terrain probe;
  pop 128, 4 workers, 240 s each): best min distance to box stuck ~255-285 (start ~465). Best candidates swing right
  along the top then fall to Y~4540: a local optimum, no launch. Fitness is deceptive for a gap crossing.
- Launch signature (`explore/launch_events.py` on the 5054 path): high-speed events (35-81 units/tick) follow
  clockwise pointer rotation of ~50 deg/decision at radius 113-128, hammer hitting terrain. My `circle` primitive
  already covers this, so sweeps were sampled ~1000+ times at the plateau without crossing.
- Hypothesis now tested (E11): the leaf is a dead end and the route continues from an earlier branch; added tier
  "high non-retained states" and denser route branch points (every 6 decisions).

## E11/E12 (no gain) and the world-map diagnosis
- E11 (route import every 6 decisions + high-non-retained tier, round 0 x 420 s x 4 islands): flat at 5055.75. Killed.
- E12 launch envelope from the plateau state (`explore/launch_envelope.py`, 4 workers x 1000 random launches per primitive family):
  apex gain max 9-21 (old primitives) / 13-43 (spin-release), p99 = 0; min distance to the next block ~200-285.
  The 5054 tower tip is not crossable in one launch.
- Offline world map (`python explore/world_map.py explore/runs/e7_seed22/best_path.json`): built from the game's own 162 level tile
  costumes (no physics): world x[-704,5808] y[-180,14972]; `explore/crop.py` for zoomed crops.
  Reading it: the route goes right to a pillar (3500,3750), crosses a plank leftwards, then climbs a tall isolated tower whose tip is
  Y~5054. The tower tip is a **decoy**: above it nothing within ~450 units.
- Geometry potential (`python explore/potential.py 3 0.3 60`, `explore/phi_trace.py`): phi(p) = cheapest cost to the top islands
  where free space costs distance x (1 + clearance/60) (so one long gap is much costlier than several short hops), upward x3,
  downward x0.3, moving over solid 0.1-0.5/unit. Descent from the tower tip goes back DOWN the tower's right face to Y~4400,
  jumps ~150-250 units to a floating blob (X1900-2250, Y4350-4600), then to a building (X2300-2700) and a thin chain (X2800-3000,
  Y4400-5000) up to the big block (X3000+, Y5000+). phi(tip)=28065 > phi(1700,4400)=27942.
  Height was a deceptive progress metric (E7-E11); this is why every search stalled at the tip.

## E13 potential-guided Go-Explore (progress = -phi instead of height)
- Code: `research/runtime.js` `setPhi` (page-side hold-test gate uses phi within `phiMargin`), `explore/goexplore.py --phi`
  (progress scalar `y`, real height `ry`). Search bookkeeping only; physics untouched.
- Smoke (`python explore/goexplore.py --phi --secs 90 --seed 31 --share-dir explore/runs/e13_smoke_share --out explore/runs/e13_smoke`,
  imports one 5054-route): retained state at **(2212.5, 4678.8)**, phi progress -28065 -> -27375, replay-verify exact + 180-tick hold held.
  That is on the floating blob past the tower decoy, ~3 min of 1 worker.
- Next: `python explore/run_islands.py --share-dir explore/runs/e13_share --rounds 3 --round-secs 420 --base-seed 1300 --stall-rounds 2 --min-gain 40 --extra "--phi --stall-s 300"`

## E13 (old potential, 2 rounds) -> E14 (surface-hugging potential): retained Y 5055 -> 9341
- E13 (potential tunnels through solid mass): round 0 reached (2463,5200) (progress -28065 -> -27028), round 1 flat. That point sits under an
  overhang of a big structure; the potential's cheapest path ran through its interior. Killed.
- Fix: solid cost density x(1 + depth/16) so the potential follows surfaces (`python explore/potential.py 3 0.3 60 16`).
  New descent from (2463,5200) climbs the structure's left surface instead.
- E14: `python explore/run_islands.py --share-dir explore/runs/e14_share --rounds 3 --round-secs 420 --base-seed 1500 --stall-rounds 2 --min-gain 40 --extra "--phi --stall-s 300"`
  (e14_share seeded with the 8 verified E13 routes to (2463,5200)).
  - round 0 (431 s): best retained (2398,6630) mid-round, round-end global progress -28166.
  - round 1 (432 s): retained **(4973.3, 9341.0)**, all four islands' bests replay-verified exact + 180-tick hold held
    (`explore/runs/e14_share_rounds/r1_s151*/summary.json`); path saved `explore/runs/e14_best_9341.json` (2326 decisions, 9424 ticks, ~2.6 game-min).
  - round 2 (407 s): flat -> supervisor stall stop.
- Plateau at 9341 (screenshot `explore/runs/e14_best_9341.png`): body against the leaning pink "Scratch Tower" (face overhangs ~12 deg, x 4975@Y9340 -> 4900@Y9700,
  continues to Y~12000), hammer pointing down planted on a small green mound. Real-renderer terrain probe (`explore/terrain_map.py`) agrees with the
  offline map here.
- E15 receding-horizon CEM with exact snapshots (`explore/mpc_climb.py`, fitness = height after a 92-tick held-pointer suffix = retained height;
  pop 64, horizon 24 decisions, 3 iters, commit 8): 120 s smoke, 7 outer steps, predicted retained end height 9322-9339 < 9341 each step: no better retained
  height within ~190 ticks of any plan. Not a climb.
- Next E16: longer persistent run (4 islands x 900 s, `--front-scale 80 --max-len 60`).

## E16, E17, held-out checks, tests (final state of this session)
- E16 (`python explore/run_islands.py --share-dir explore/runs/e14_share --out-root explore/runs/e16_rounds --rounds 1 --round-secs 900 --base-seed 1600 --stall-rounds 1 --min-gain 40 --extra "--phi --front-scale 80 --max-len 60"`):
  4 islands x 910 s, longer segments (<=60 decisions), softer frontier weighting: **zero gain**, retained stays (4973,9341); transient max 9523.
- E17 goal-box CEM above the bulge (box X4900-4990, Y9780-9900; horizon 96, pop 128): **invalid / inconclusive** - launched with `(cmd &)` inside a normal
  shell call, so the processes were killed when the call returned after iteration 0 (best minD 428-439 vs start ~440). Not re-run (63 s/iteration with 4 workers;
  MPC retained-fitness search already showed no better held height within ~190 ticks).
- Replay of the best route (`python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 1 2 3 --noise 0 0.25 2 --trials 2 --hold-ticks 180`):
  reset seeds 0,1,2,3 all end at exactly (4973.256002255466, 9341.049378508918) at tick 9424, 180-tick hold held (same on every seed: the game's RNG does not
  influence this route). But with pointer noise of only 0.25 (std, out of +-128) 8 of 10 noisy runs die or stall below Y~760; noise 2.0 likewise. So this is a
  verified open-loop trace, **not a robust feedback policy**.
- Tests after all runtime edits: `python -m unittest discover -s tests -q` -> 511 tests OK; `node tests/collision_memo.test.js` OK. Physics code untouched
  (only search bookkeeping: snapshot/restore, cell archive, hold test, rollout batch, optional potential grid).

## Status
- **SUCCESS (Y > 16000) reached on the real game, open-loop**: `explore/runs/e28_SUCCESS_s3100.json`, verified on fresh resets seeds 0-3 (see E26-E28 below). Earlier: retained height 10808 (`e25_best_10808.json`).
- Previous best: retained height **9341.0 (X 4973.3)**, 58% of the summit height (16000), from ordinary spawn, 2326 decisions x 4 ticks = 9424 ticks (~2.6 game-min),
  fresh-reset replay bit-exact, 180-tick hold stable. Prior RL best in this repo: Y 96. **Summit NOT reached; no policy distilled.**
- Remaining blockers: (1) the bulge/overhang of the leaning "Scratch Tower" face at Y 9400-9800 (X 4900-4975) resisted Go-Explore (about 1 h of 4-core time),
  receding-horizon CEM and goal CEM; (2) beyond the tower the map only has isolated floating islands separated by ~500-1500 unit gaps (Y 12000-15000), and the
  game's Y>16000 win line is above the last tile (14972), so the finish itself is unexplored.

## E18-E25: leaving the column crux via the west ramp (58% -> 67.5%)
- E18 (gait-aligned primitives, `--gait-frac 0.6 --local-radius 600`, 4 islands x 539 s at the Y 9341 column pocket): zero gain.
- E19 (goal = floating platform P2 at X 4250-4500, Y 9900-10100; `PHI_TAG=_p2`): zero gain, the search just returns to the pocket.
- Map reading (`explore/world/crop_P.png`, `crop_R.png`): the column face at Y 9340-9740 is a ~15 deg overhang, and the screenshot shows the verified
  9341 state is the cat standing on a green mound under it, not climbing. West of the staircase there is a chain of round "ball stones" (Y ~8800),
  a blob (X 2150-2450), a cage structure, and a ~55 deg slope ramp (X 2650-3500, Y 9300-10500) that leads to a plateau (Y ~10600) with a chalice,
  umbrella cap and the pagoda spire (to Y ~12000).
- Fix 1: the offline potential can be re-aimed (`PHI_TAG`, `PHI_GOAL_BOX=xa,xb,ya,yb`, `PHI_COVER=k` penalises free space under ceilings so the
  potential cannot route around the underside of a bulge). `goexplore.py` gates with `PHI_MAXX` / `PHI_MINY` (cells outside rank last) to forbid
  returning to the known column dead end. Staged goals: E20/E20b (ramp goal, pocket/base-top local minima, flat), E21 (goal = blob at X 2150-2450:
  reached in <280 s), E22 (ramp goal without `PHI_COVER`: trapped under the ramp nose at (2694, 9120)), E23 (`PHI_COVER=6`, goal = ramp top):
  retained Y 10186 in 800 s, E24c/E25 (`PHI_COVER=6`, full goal, `PHI_MAXX=4600`, import margin 250): retained **Y 10808 at X 3934** (chalice left scroll).
- Pitfalls found: (1) sharing files from runs with different potentials in one share dir breaks island ranking (units differ) - use a fresh share dir
  per potential; (2) with a fast-moving frontier, islands re-import each other's routes (~20 s each) and starve - raise `--import-margin`.
- Verified: `python explore/replay_route.py explore/runs/e25_best_10808.json --seeds 0 1 2 3 --hold-ticks 180` -> tick 11924, x 3934.04, y 10808.0,
  held true on all four reset seeds (bit-identical). Route file: `explore/runs/e25_best_10808.json` (2951 decisions x 4 ticks); earlier `e24_best_10802.json`.
- **E26 (full potential, `PHI_COVER=6`, `PHI_MAXX=4600`, `--gait-frac 0.4 --local-radius 250 --front-scale 30`)**: one island passed the chalice/umbrella cap, climbed the
  pagoda spire (Y 11000-11900), flung to the sky islands and stood retained on the Y 14564 island (X 3138) within the first 600 s round
  (`explore/runs/e26_best_14564.json`, 3320 decisions, replay held on seeds 0-3). The other three islands crashed with `ValueError: Probabilities contain NaN`
  (pick weights all zero under `--local-radius`; not fixed).
- **E27/E28 (plain height progress, no potential, from the Y 14564 route)**: E27 reached success inside the page in 42 s but the saved SUCCESS_path was the best
  retained node, not the successful segment (bug). Fixed in `goexplore.py` (`success_actions = path(picked node) + segment[:decisions]`).
  E28 re-ran: all 4 islands reached success in 69 s. Fresh-reset replay of `explore/runs/e28_SUCCESS_s3100.json` (3455 decisions, 13937 ticks):
  **y 16000.8189, success true on reset seeds 0, 1, 2, 3 (bit-identical)**. Last leg: retained at (3569, 14884), then a smooth ~10 units/tick vertical rise to 16000 (a game mechanic, not understood).
- Robustness: open-loop only. `--noise 0.01` and `0.25` both die at Y ~260-340 (tick ~4700-5300). No feedback policy exists.
- (superseded) previous blocker: the scroll below the umbrella cap of the chalice (X 3925-3990, Y 10800-10930): 2 rounds x 4 islands flat (max transient Y 10970).

## Reproduce (from a clean checkout, Python 3.12 venv with requirements-research.txt + huggingface_hub httpx scipy pillow; Chrome present)
    export PYTHONPATH=$PWD RL_CHROME_NO_SANDBOX=1
    python explore/world_map.py explore/runs/e7_seed22/best_path.json      # offline world map (world/*.npy are git-ignored, regenerable)
    python explore/potential.py 3 0.3 60 16                                  # geometry potential phi.npy / phi_x4.npy
    python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 1 2 3 --hold-ticks 180   # verify best route (needs no potential)
Search used 4 parallel Chrome workers (~1 GB each; cgroup limit 7 GB); never start extra Chrome while 4 islands run.

## E31: closed-loop policies (behaviour cloning, MPC, tracking)
- **Why this matters.** Everything above is an open-loop trace: `--noise 0.01` already breaks it. A policy has to
  act from whatever state it is in. Four closed-loop approaches were built and measured; three stall near spawn,
  one reaches the summit.
- **Behaviour cloning** (`explore/policy_bc.py`): 25 game state features -> pointer offset. Trained on all four
  verified routes (12,052 decisions, 200 epochs, MSE 1100 units^2 ~ 33 pointer units RMS). Closed loop on
  held-out seeds 9001/9002/9003, 150 s each: **max Y 158.28 on all three, final Y 49.0, identical every time** -
  it converges to one looping behaviour and never climbs. Compounding error: it only ever saw reference states.
- **MPC on the real game, height objective** (`explore/policy_mpc.py`): receding-horizon CEM, fitness = retained
  height after a held suffix. 300 s, 324 decisions (4 ticks/s - the planner is the bottleneck): **max Y 174.9**.
- **MPC with the geometry potential** (same file, `--phi --phi-tag _full2`): 600 s, 2790 decisions, 19 ticks/s:
  **max Y 177.9, final Y -9**. Global cost-to-goal guidance did not help at this horizon.
- **Tracking controller** (`explore/policy_track.py`): the verified route is treated as a *reference* (position per
  tick). At each decision the controller compares the live state with the reference; on reference it applies the
  reference action, off reference it re-plans a short pointer plan with the real game as the simulator, aiming at
  the reference `horizon` decisions ahead, and commits the first few decisions. A phase estimator matches the live
  position against a forward window of reference points so a deviation does not lose the reference.
  - **Noise 0, seeds 0 and 1: reaches the summit, `success: true`, tick 13937, x 3589.2328706585417,
    y 16000.818689285075 - bit-identical to the open-loop reference, 0 replans, max deviation 0.0.** The
    controller is exact when it can be.
  - **Noise 0.25 (the perturbation that kills the open loop at tick ~5300, Y -206), 1600 decisions / 6400 ticks:**
    both variants stay alive to the decision cap (open loop is dead by then). Final Y 516.0 without phase
    re-synchronisation, 169.4 with it; mean deviation 1360-1833 units either way. Honest reading: feedback keeps
    the run alive past the open-loop death point, but at this noise the deviation is far outside the basin where
    this reference is a useful target, so neither variant is actually tracking, and neither climbs.
- **Honest bottom line.** The only thing that reaches the summit is the verified open-loop route; the closed-loop
  controller also reaches it, but only by staying exactly on that route. No learned or planning policy that climbs
  from arbitrary states was obtained in this session. The infrastructure for all four approaches is committed and
  reproducible (`policy_bc.py`, `policy_mpc.py`, `policy_track.py`, `policy_dagger.py`).
- Cost note: the MPC planners run at 4-19 ticks/s (the planner, not the game, is the bottleneck), which is why
  their budgets buy so few decisions; the tracking controller runs at 220 decisions/s on reference.

## Viewing / verification tooling (no new searches)
- `explore/replay_route.py`: `--headed`, `--speed`, HUD overlay, `--trace-out`, `--compare-trace` (first-divergence report, exit code 3 on divergence).
  `research/cdp_browser.py` + `research/browser_bridge.py`: CDP launch/attach (no chromedriver), Windows Chrome detection, automatic CDP fallback.
  Setup and success criteria: `LOCAL_REPLAY.md`.
- Reference trace exported from the verified cloud run (Linux x86_64, headless Chrome 154, Python 3.12.3):
  `python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 --hold-ticks 180 --trace-out explore/reference/e14_best_9341.trace.jsonl`
  (ticks 121..9604 = 9304 route ticks + the 180-tick hold; full-precision floats).
- Same-host checks: Selenium launch vs CDP launch (`RL_BROWSER_DRIVER=cdp ... --compare-trace`, seeds 0 and 1): BIT-EXACT over all ticks.
  Cross-host determinism is unmeasured; the route is chaotic (0.25 pointer noise breaks it), so use `--compare-trace` locally.
- The 9424 "ticks" quoted earlier is the game tick counter (120 warm-up ticks inside reset + 9304 route ticks).

## Recording the verified 9341 route (viewing only; no new searches)
- Confirmation: `python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 --hold-ticks 180`
  -> tick 9424, x 4973.256002255466, y 9341.049378508918, held true.
- Headed replay on the cloud host: Xvfb (`xvfb-run -a -s "-screen 0 1100x820x24"`) + ffmpeg x11grab, speed 1.
  Artifacts in `explore/runs/e14_recording/`: `e14_best_9341_headed_full.mp4` (5:29, 1100x820@30),
  `contact_sheet.png` (10 frames), `recording.trace.jsonl`, `replay_stdout.log`, `divergence_report.json`.
  The recorded run's trace is **bit-exact** vs the reference (final delta [0.0, 0.0]); HUD shows the
  `HOLD COMPLETE 180/180: HELD` banner and the FINAL line.
- Measured failure mode fixed while recording: a headed Chrome with an accelerated 2D canvas diverges from the
  reference at **tick 2000** (one ULP, then chaos -> Y~286). Cause: rasterization of the SVG skin silhouettes that
  feed collision. Fix (now automatic for headed launches in both the CDP and Selenium paths):
  `--disable-accelerated-2d-canvas`. Rendering cadence (every tick vs never) is *not* the trigger; the GL/canvas
  backend is. `RL_CHROME_EXTRA_FLAGS` added for further experiments (e.g. `--disable-gpu-rasterization`).
- This is very likely the same class of failure seen on the user's Windows machine (which also diverged at tick 2000):
  worth retrying there with the automatic flag and `--compare-trace`.

## Recording the summit route (viewing only; no new searches)
- Confirmation: `python explore/replay_route.py explore/runs/e28_SUCCESS_s3100.json --seeds 0 1 2 3 --hold-ticks 0`
  -> tick 13937, x 3589.2328706585417, y 16000.818689285075, **success true** on all four reset seeds (bit-identical).
- Headed recording under Xvfb + ffmpeg x11grab at speed 1 (`explore/runs/e28_recording/`):
  `e28_success_headed_full.mp4` (7:53, 1100x820@30), `contact_sheet.png` (10 frames), `recording.trace.jsonl`,
  `replay_stdout.log`, `divergence_report.json`. Recorded run trace **BIT-EXACT** vs `explore/reference/e28_success_16001.trace.jsonl`
  (final delta [0.0, 0.0]); HUD shows the green SUCCESS banner and the FINAL line with success=True.
- Viewing-only changes: HUD success banner + `success=` field in the FINAL line; `hud_text` tests.
- Fixed the E26 crash: `pick()` now zeroes non-finite tier weights and falls back to uniform when the tier
  leaves all weights at zero (regression test `tests/test_explore_pick.py`). Suite: 521 tests OK + node test OK.

## E29: the game's own ending (viewing only; no new searches)
- Why it never showed: the harness stopped stepping the moment world Y passed 16000, so the project's own
  finish path never ran. The path is `Player` main loop exits above 16000 -> broadcast `SAVE TIME TO CLOUD`
  -> `High Score` compares the time -> broadcast `Win` or `Win - Record` -> `Splash` fades to black, shows
  the end title over a scrolling star field -> `Cursor` hides.
- Two viewing-only changes: `step(commands, after=True)` keeps stepping past the win flag
  (`replay_route.py --after-success N`, default pointer neutral), and `--presentation` (default on with
  `--after-success`) reproduces the title-screen presentation state the real game only reaches through its
  title screen: Splash visible at ghost 100 plus the Timer's six digit clones (via the project's own
  `splash - hit` / `Show Score` scripts). No RNG draw, no variable the physics reads, no collision drawable.
- Verified: `--seeds 0 1 2 3 --after-success 1200 --trace-out ... --compare-trace ...` -> **BIT-EXACT** on all
  four seeds with 1200 extra ticks (final delta [0.0, 0.0]). Success line unchanged (tick 13937, y 16000.8189).
- The ending shows the game's own finish time (`TIME` digits, `7'44` for this route) and `New World Record!`
  by default; `--fastest-frames 3000` emulates a populated leaderboard and shows `You Got Over It!`.
- Recorded under Xvfb + ffmpeg x11grab at speed 1 (`explore/runs/e28_ending_recording/`):
  `e28_success_ending_full.mp4` (8:45, 1100x820@30), `ending_clip.mp4` (0:52, the ending only),
  `end_title_frame.png`, `contact_sheet_ending.png`, `recording.trace.jsonl`, `replay_stdout.log`,
  `divergence_report.json` (BIT-EXACT, 1500 extra ticks).

## E30: baselines and ablations (equal budget, 3 seeds, 4 islands)
- Program: `explore/experiments.py` (`list` / `run` / `table`), driver `explore/run_experiments.sh`.
  Every config-seed is 4 Go-Explore islands in parallel on 4 cores for a fixed wall-clock budget; configs that
  start from a verified route republish it into a fresh share dir so the islands import it at their first sync
  (in the units the islands compare: height, or -phi under `--phi`).
- `--no-hold-test` ablation added (`goexplore.py`, `runtime.js`): accept frontier states without the retained
  (pointer-frozen) hold test, so flung/airborne height counts as progress. Baseline `explore/random_restart.py`:
  same action interface and hold test, no cell archive, no potential, restart from spawn after a stall.
- **Results** (3 seeds x 4 islands per config, fixed seeds 5100/5200/5300, `explore/runs/experiments/results.jsonl`;
  every config-seed is a fresh share dir with the start route republished in the units the islands compare):

| suite | config | budget | best retained progress | units | summit reached |
|---|---|---|---|---|---|
| baselines | go-explore (height) | 240s x 4 | 3747.5 | height | 0/3 |
| baselines | random restart | 240s x 4 | 2281.3 | height | 0/3 |
| last_leg | full | 150s x 4 | 16005.7 | height | 3/3 |
| last_leg | no hold test | 150s x 4 | 16010.4 | height | 3/3 |
| last_leg | no gait moves | 150s x 4 | 16005.6 | height | 3/3 |
| last_leg | with potential | 150s x 4 | -0.0 (phi) | phi | 3/3 |
| mid_leg | full | 300s x 4 | -27700.2 (start, no gain) | phi | 0/3 |
| mid_leg | no potential | 300s x 4 | 10808.7 | height | 0/3 |
| mid_leg | no ceiling penalty | 300s x 4 | -16052.4 | phi | 0/3 |
| mid_leg | no gait moves | 300s x 4 | -13640.5 | phi | 0/3 |
| staged_goals | final goal | 240s x 4 | -28979.6 (start, no gain) | phi | 0/3 |
| staged_goals | stage-1 ramp goal | 240s x 4 | -2500.6 (start, no gain) | phi | 0/3 |

- **What the ablations do and do not show.** They are honest but weaker than the original E-runs, because the
  budget had to be cut to fit a 3-seed program: E24-E26 used 600-800 s per island and several rounds, these runs
  get 240-300 s and one round.
  - **From spawn (informative).** Go-Explore beats random restarts with the same interface, hold test and budget:
    3747 vs 2281 retained height. Neither reaches the summit in 4 minutes; the E-series needed ~45 min of 4-island
    time to pass the same terrain, so this is a budget statement, not a method statement.
  - **Last leg (saturated).** Every variant succeeds on every seed in under 60 s, including with the hold test
    removed and with the gait generator off. The start route is 1100 units from the finish, so this suite cannot
    separate anything; it does show the last leg is easy from a good start state.
  - **Mid leg and staged goals (budget-limited, flat).** No config beat its start route. The height baseline
    gained 0.7 units; the phi configs gained nothing (their "progress" equals the start route's own value). Two
    variants show transient excursions the retained metric rejects (no_gait 13449.7, no_ceiling_penalty 12672.0),
    which is exactly what the hold test exists to filter. To say anything about the potential, the ceiling penalty
    or staged goals, these need the original 600-800 s budgets; at 300 s every variant is at the start.
  - Honest summary: the program confirms the baseline ordering and the mechanics of each ablation, and it shows
    the potential/ceiling/staging questions are **not** answerable at this budget. The E18-E28 evidence for those
    (LOG above) was collected at 600-800 s per island and is the stronger evidence.
