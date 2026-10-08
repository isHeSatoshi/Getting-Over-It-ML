# UPDATE: the game's own ending (win animation, finish time, end title)

`explore/runs/e28_SUCCESS_s3100.json` (3455 pointer decisions x 4 ticks, open loop) reaches `success` (world Y 16000.8189) from ordinary spawn on the real game:

    python explore/replay_route.py explore/runs/e28_SUCCESS_s3100.json --seeds 0 1 2 3 --hold-ticks 0
    # headed + trace compare against the reference trace exported from the cloud host:
    python explore/replay_route.py explore/runs/e28_SUCCESS_s3100.json --headed --speed 4 --hold-ticks 0 --trace-out local.trace.jsonl --compare-trace explore/reference/e28_success_16001.trace.jsonl
    # watch the ending: keep stepping 1500 ticks (50 s) past the win flag
    python explore/replay_route.py explore/runs/e28_SUCCESS_s3100.json --headed --speed 1 --hold-ticks 0 --after-success 1500

Expected final line: tick 13937, x 3589.2328706585417, y 16000.818689285075, success true (bit-identical on reset seeds 0-3 on the cloud host).
Same caveats as below: this is an open-loop trace (any pointer noise, even std 0.01, makes it fall), and cross-host determinism is unmeasured; use `--compare-trace`.
The sections below describe the earlier Y 9341 route and tooling (still valid, same commands).

## The ending (what the harness used to cut off)

The harness stops stepping as soon as world Y exceeds 16000. The game's own finish path is: the Player
main loop exits above 16000 and broadcasts `SAVE TIME TO CLOUD`; `High Score` compares the time and
broadcasts `Win` (or `Win - Record`); `Splash` fades to black and shows the end title over a scrolling
star field; `Cursor` hides. None of that ran before.

`--after-success N` keeps stepping N ticks past the win flag (neutral pointer, still the real game).
The ending also needs the presentation state the real game only reaches through its title screen, so
`--presentation` (on by default with `--after-success`) reproduces it: the Splash sprite visible at
ghost 100 and the Timer's six digit clones, using the project's own scripts. It draws no random number
and writes no variable the physics reads; the recorded run is **BIT-EXACT** against the reference trace
with 1500 extra ticks (final delta [0.0, 0.0]).

What you see: the finish time (the game's own `TIME` digits, e.g. `7'44`), then either

- `New World Record!` (default: with no cloud leaderboard the game treats any time as a record), or
- `You Got Over It!` with `--fastest-frames 3000` (emulates a populated leaderboard; 3000 frames = 100 s).

`--ending-speed N` plays that phase at N x real time.

## Baselines, ablations and policies (what was measured, and what failed)

Everything below is reproducible from this branch. Results table: `explore/runs/experiments/results.jsonl`
(render it with `python explore/experiments.py table`); full notes in `explore/LOG.md` (E30, E31).

    python explore/experiments.py list
    python explore/experiments.py run --suite baselines --seeds 5100 5200 5300 --secs 240 --workers 4
    python explore/experiments.py table

Measured, 3 seeds x 4 islands per config: from spawn, Go-Explore beats random restarts (3747 vs 2281 retained
height in 240 s); the last leg succeeds for every variant (the start route is 1100 units from the finish, so that
suite cannot separate anything); at a 300 s budget the mid-leg potential / ceiling-penalty / gait ablations are all
flat at their start route, so those questions are **not** answerable at that budget (the E18-E28 evidence was
collected at 600-800 s per island).

Policies (`explore/policy_bc.py`, `explore/policy_mpc.py`, `explore/policy_track.py`, `explore/policy_dagger.py`):

    # closed-loop tracking controller: reaches the summit when the run stays on the reference
    python explore/policy_track.py --route explore/runs/e28_SUCCESS_s3100.json --seeds 0 1 --noise 0
    # the same controller under the noise that kills the open loop (slow: it replans)
    python explore/policy_track.py --seeds 0 --noise 0.25 --trials 1 --max-decisions 1600
    # behaviour cloning and MPC
    python explore/policy_bc.py collect --routes explore/runs/e28_SUCCESS_s3100.json explore/runs/e26_best_14564.json
    python explore/policy_bc.py train --data explore/runs/policy_bc/data.npz --out explore/runs/policy_bc
    python explore/policy_bc.py eval --model explore/runs/policy_bc/model.pt --seeds 9001 9002 9003 --secs 150
    python explore/policy_mpc.py --out explore/runs/p_mpc_phi --secs 600 --phi --phi-tag _full2

Honest results: behaviour cloning stalls at Y 158 on every held-out seed; MPC stalls at Y ~175 with either the
height or the potential objective. The tracking controller reaches the summit **bit-exactly** (0 replans, max
deviation 0.0) when the run stays on the reference, and under noise 0.25 it stays alive past the tick where the
open loop dies but does not climb. **No policy that climbs from arbitrary states was obtained.**

## Recorded ending video
`explore/runs/e28_ending_recording/`:

- `e28_success_ending_full.mp4` (8:45, 1100x820, 30 fps): the whole route at real time plus 50 s of ending and the linger.
- `ending_clip.mp4` (0:52): just the ending.
- `end_title_frame.png`, `contact_sheet_ending.png`: stills of the end title.
- `recording.trace.jsonl`, `replay_stdout.log`, `divergence_report.json`: BIT-EXACT, 1500 extra ticks, final delta [0.0, 0.0].

## Recorded reference video (summit run)
`explore/runs/e28_recording/` contains a full headed recording of the summit route, made on the cloud host under Xvfb
(no monitor attached) with ffmpeg x11grab, real time:

```bash
xvfb-run -a -s "-screen 0 1100x820x24" bash -c '
  export RL_CHROME_CONTAINER=1
  ffmpeg -y -f x11grab -framerate 30 -video_size 1100x820 -i "$DISPLAY" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p explore/runs/e28_recording/e28_success_headed_full.mp4 &
  sleep 3
  python explore/replay_route.py explore/runs/e28_SUCCESS_s3100.json --seeds 0 --headed --speed 1 --hold-ticks 0 --linger 6 \
    --trace-out explore/runs/e28_recording/recording.trace.jsonl \
    --compare-trace explore/reference/e28_success_16001.trace.jsonl \
    --report-out explore/runs/e28_recording/divergence_report.json'
```

Artifacts: `e28_success_headed_full.mp4` (7 min 53 s, 1100x820, 30 fps, the whole route at real time ending on the
green `*** SUCCESS: world Y > 16000 (summit) reached ***` banner and the `FINAL ... success=True` line),
`contact_sheet.png` (10 frames across the run), `recording.trace.jsonl` (per-tick trace of the recorded run),
`replay_stdout.log`, `divergence_report.json`. The recorded run is **bit-exact** against the reference trace
(final delta [0.0, 0.0]).

What success looks like for this route (also printed by the headless command above):

- Final line: `tick 13937 x 3589.2328706585417 y 16000.818689285075 max_y 16000.818689285075 dead=False success=True`.
  Pass tolerance within +-0.001 per axis; bit-exact hosts give 0.
- The HUD shows `*** SUCCESS: world Y > 16000 (summit) reached ***` when the harness `success` flag fires (it mirrors the project's own finish condition: the Player script's main loop is `repeat until PLAYER Y > 16000 or PLAYER Y < -180`, and on exit above 16000 it broadcasts `SAVE TIME TO CLOUD`; the end title itself was not watched because the harness stops stepping at success).
- `--hold-ticks 0` for this route (it ends in the success state; the hold test does not apply).

---

# Replaying the verified 9341 route locally (headed Chrome)

**Scope.** This replays one saved open-loop route (`explore/runs/e14_best_9341.json`, 2326 pointer decisions x 4 ticks)
on the real compiled game from ordinary spawn. It reaches **Y 9341.049, not the summit (Y > 16000)**. Viewing and
verification tooling only: physics, rewards and the route are unchanged.

## Determinism: read this first
I do **not** promise cross-host bit-exactness. What I measured:

| Check | Result |
|---|---|
| Reset seeds 0, 1, 2, 3 (same host) | identical end state and identical per-tick trace |
| Selenium launch vs CDP launch (same host) | per-tick trace **bit-exact** (`--compare-trace`, 9484 ticks) |
| Linux x86_64, headless Chrome 154, Python 3.12.3 | reference trace in `explore/reference/` was produced here |
| Headed Chrome on Linux under Xvfb, recorded run | per-tick trace **bit-exact** with the software-canvas flag below |
| Any other OS / Chrome version / GPU / display scale | **not measured** |

**Important measured failure mode (likely what you hit on Windows).** A headed Chrome whose 2D canvas is
GPU-accelerated diverges from the reference at **tick 2000** by one ULP, which chaos amplifies into a completely
different run (Y ~286, falls). The cause is rasterization of the SVG skin silhouettes that feed collision.
Fix, now automatic for headed CDP launches: `--disable-accelerated-2d-canvas`. With it, the recorded headed run
is bit-exact over all 9484 ticks. If your local run still diverges at tick 2000, try adding
`--disable-gpu-rasterization` via `RL_CHROME_EXTRA_FLAGS` and send `divergence_report.json`.

Why it may be host-sensitive: the game's collision uses Chrome's real renderer (costume rasterisation and silhouettes),
and the route is chaotic (pointer noise of only 0.25 out of +-128 already breaks it), so a one-bit difference anywhere can
grow into a completely different run. If your machine differs, do not trust the final position alone: run with
`--compare-trace`, which reports the first tick where you diverge from the reference and how far, and send me
`divergence_report.json`. `--force-device-scale-factor=1` is set for CDP launches to remove Windows display scaling as a variable.

## Fresh-machine setup
- Python 3.11 or 3.12 (x64). The repo pins are "tested 3.11"; the reference was produced on 3.12.3.
- Google Chrome (stable, ideally major version 154 to match the reference; Edge is used only as a last-resort fallback).
- Replay needs only `websockets` (and `selenium` if you choose the Selenium path; `numpy` only for `--noise`).

bash (Linux/macOS/Git Bash):
```bash
git clone -b explore-9341 https://github.com/isHeSatoshi/Getting-Over-It-ML.git && cd Getting-Over-It-ML
python3 -m venv .venv && source .venv/bin/activate
pip install websockets==15.0.1 selenium==4.41.0 numpy==2.4.3
export PYTHONPATH="$PWD"
export RL_BROWSER_DRIVER=cdp                 # skip chromedriver entirely
# export RL_CHROME_BINARY="/path/to/chrome"  # only if auto-detection fails
# export RL_CHROME_NO_SANDBOX=1              # only in root/containers
```

PowerShell (Windows 10/11):
```powershell
git clone -b explore-9341 https://github.com/isHeSatoshi/Getting-Over-It-ML.git; cd Getting-Over-It-ML
py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install websockets==15.0.1 selenium==4.41.0 numpy==2.4.3
$env:PYTHONPATH = (Get-Location).Path
$env:RL_BROWSER_DRIVER = "cdp"               # default on Windows already; explicit is fine
# $env:RL_CHROME_BINARY = "C:\Program Files\Google\Chrome\Application\chrome.exe"   # only if auto-detection fails
```
(If script activation is blocked: `Set-ExecutionPolicy -Scope Process Bypass`.)

## The one-line headed replay
bash:
```bash
python explore/replay_route.py explore/runs/e14_best_9341.json --headed --speed 4 --hold-ticks 180 --trace-out local.trace.jsonl --compare-trace explore/reference/e14_best_9341.trace.jsonl
```
PowerShell:
```powershell
python explore\replay_route.py explore\runs\e14_best_9341.json --headed --speed 4 --hold-ticks 180 --trace-out local.trace.jsonl --compare-trace explore\reference\e14_best_9341.trace.jsonl
```
`--speed N` plays at N x real time (1x = the game's 30 ticks/s; the route is 9304 ticks, about 5 min at 1x, about 78 s at 4x;
very high speeds are limited by your CPU/render rate). The window stays open 10 s at the end (`--linger`).
The HUD (top-left) shows tick (the counter includes the 120 warm-up ticks of reset), X/Y at full precision, max Y so far,
gain since spawn (provisional), hold drift, and a green banner `HOLD COMPLETE 180/180: HELD` when the 180-tick hold passes
(red `NOT HELD` otherwise). The final position is also printed as a `FINAL ...` line.

Headless regression (same as before): `python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 1 2 3 --hold-ticks 180`

## Recorded reference video
`explore/runs/e14_recording/` contains a full headed recording made on the cloud host under Xvfb
(no monitor attached), captured with ffmpeg x11grab. These artifacts live on branch `explore-9341-recording`
(which is `explore-9341` plus one recording commit):

```bash
xvfb-run -a -s "-screen 0 1100x820x24" bash -c '
  export RL_CHROME_CONTAINER=1
  ffmpeg -y -f x11grab -framerate 30 -video_size 1100x820 -i "$DISPLAY" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p explore/runs/e14_recording/e14_best_9341_headed_full.mp4 &
  sleep 3
  python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 --headed --speed 1 --hold-ticks 180 --linger 6 \
    --trace-out explore/runs/e14_recording/recording.trace.jsonl \
    --compare-trace explore/reference/e14_best_9341.trace.jsonl \
    --report-out explore/runs/e14_recording/divergence_report.json'
```

Artifacts: `e14_best_9341_headed_full.mp4` (5 min 29 s, 1100x820, 30 fps, the whole route at real time including the
hold and the FINAL line), `contact_sheet.png` (10 frames across the run), `recording.trace.jsonl` (per-tick trace of
the recorded run), `replay_stdout.log` (JSON result + FINAL line + `COMPARE ... BIT-EXACT`), `divergence_report.json`.
The recorded run is **bit-exact** against the reference trace (final delta [0.0, 0.0]).

## What success looks like
- Final route position **x = 4973.256002255466, y = 9341.049378508918** at tick counter 9424. Pass tolerance: within **+-0.001** on each axis
  (equivalently the printed `FINAL` line rounds to 4973.256 / 9341.049). On a bit-exact host the difference is exactly 0.
- 180-tick hold: `held: true`, i.e. final Y > route-end Y - 6 and |dX| < 12. Reference: x 4974.478889239314, y 9338.878770709565.
- `dead: false`, `success: false` (the summit is not reached by this route).
- `COMPARE ...: BIT-EXACT` (best), `WITHIN-EPS` (tiny drift, default eps 1e-6), or `DIVERGED` (exit code 3). A `DIVERGED` result
  with a late first-divergence tick is still useful data: it tells us where your host starts to differ.
- `divergence_report.json` (`--report-out`): verdict, first bit-level difference, first divergence over `--eps`, max deviation, final delta,
  and the reference/local environment metadata (user agent, platform, devicePixelRatio, Python).

## Windows launcher details
- **Chrome detection** (`research/cdp_browser.py`): `RL_CHROME_BINARY`; then `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%`, `%LOCALAPPDATA%`
  `\Google\Chrome\Application\chrome.exe`; then the `App Paths\chrome.exe` registry key (machine, then user); then Edge `msedge.exe`.
  macOS and Linux paths are also covered.
- **chromedriver**: the CDP path does not use it. `RL_BROWSER_DRIVER=selenium` uses Selenium Manager or `RL_CHROMEDRIVER=<path>`; if that launch
  fails (e.g. a chromedriver crash) the bridge warns and falls back to CDP automatically (`RL_BROWSER_DRIVER_FALLBACK=0` disables the fallback).
  Windows defaults to CDP.
- **CDP launch** (default on Windows): starts a fresh Chrome with its own temporary profile and an ephemeral debugging port (read from
  `DevToolsActivePort`), attaches over a websocket to the game page, and deletes the profile afterwards. It does not touch your normal Chrome profile.
- **CDP attach**: start Chrome yourself, then point the replay at it (a new tab is opened and closed):
  ```powershell
  & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\rl-attach"
  $env:RL_CDP_URL = "http://127.0.0.1:9222"
  ```
- Localhost HTTP calls bypass system proxies. Everything binds to 127.0.0.1 only. If Windows Firewall prompts for Python or Chrome, allow private/localhost.
- Troubleshooting: "Chrome not found" -> set `RL_CHROME_BINARY`; "Chrome exited early" -> close other automation, try without `--headed` first;
  `ModuleNotFoundError: research` -> `PYTHONPATH` not set to the repo root; the page never becomes ready -> confirm `Getting Over It v1/research.html`
  exists and antivirus is not blocking the local server.

## Status of this tooling
Implemented and tested on Linux: headless and headed (under Xvfb) runs, Selenium and CDP launch paths, trace export/compare,
and the full recorded capture above. **Windows code paths and a Windows headed window are still untested**; report anything
odd and I will fix it. The most likely Windows-specific issue is the canvas-rasterization divergence described at the top;
the headed flag that fixes it is applied automatically, and `RL_CHROME_EXTRA_FLAGS` exists for further experiments.
