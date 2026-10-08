"""Replay a saved route on the real compiled game from ordinary spawn and report where it ends.

The route is a list of pointer offsets in [-128,128]^2, each held for `hold` (4) ticks: exactly the
policy action interface. No snapshots are involved; this is a fresh reset + straight replay. Viewing and
verification options below never touch physics or the route.

  python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 1 2 3 --hold-ticks 180
  python explore/replay_route.py ROUTE.json --headed --speed 4 --hold-ticks 180      # visible Chrome + HUD
  python explore/replay_route.py ROUTE.json --hold-ticks 180 --trace-out my_trace.jsonl \
      --compare-trace explore/reference/e14_best_9341.trace.jsonl                    # cross-host drift check
  python explore/replay_route.py ROUTE.json --noise 0 0.25 --trials 2                # open-loop brittleness probe
  python explore/replay_route.py ROUTE.json --headed --after-success 1200 --ending-speed 1   # play the game's ending
  python explore/replay_route.py ROUTE.json --after-success 1200 --presentation --fastest-frames 3000   # normal "Win" end title

Environment: RL_BROWSER_DRIVER=cdp|selenium (Windows defaults to cdp), RL_CHROME_BINARY, RL_CDP_URL (see LOCAL_REPLAY.md).
"""
import argparse, json, sys, time
from pathlib import Path
from research.fast_bridge import FastBridge

SPAWN_Y = 21.0
# Stage variable the game's own win path compares against: with an empty cloud leaderboard the game
# broadcasts "Win - Record" (its rule: fastest < 10 frames counts as empty), so the ending shows the
# world-record screen. --fastest-frames emulates a populated leaderboard (viewing only).
SET_FASTEST_JS = ("(n) => { const st = window.vm.runtime.getTargetForStage();"
                  " const v = Object.values(st.variables).find(v => v.name === '\u2601 FASTEST');"
                  " if (!v) throw new Error('missing FASTEST'); v.value = String(n); return v.value; }")
HOLD_DY, HOLD_DX = 6.0, 12.0          # same retained-hold test used by the search


def env_meta(b):
    info = b.evaluate("({ua: navigator.userAgent, platform: navigator.platform, dpr: window.devicePixelRatio, "
                      "research: window.research.metadata()})")
    return {"user_agent": info.get("ua"), "platform": info.get("platform"), "devicePixelRatio": info.get("dpr"),
            "stage": [info["research"].get("stageWidth"), info["research"].get("stageHeight")],
            "frame_rate": info["research"].get("frameRate"), "python": sys.version.split()[0], "os": sys.platform}


def hud_text(seed, speed, tick, total, phase, hold_i, hold_n, x, y, max_y, route_end, outcome, success=False):
    lines = [f"Getting Over It  route replay   seed {seed}   speed {speed:g}x",
             f"tick {tick:6d} / {total}   [{phase}]" + (f" {hold_i}/{hold_n}" if phase != "ROUTE" and hold_n else ""),
             f"X {x!r}", f"Y {y!r}", f"max Y so far {max_y!r}"]
    if route_end is None:
        lines.append(f"gain since spawn  {y - SPAWN_Y:+.3f}")
    else:
        lines.append(f"hold drift  dY {y - route_end[1]:+.4f}  dX {x - route_end[0]:+.4f}"
                     f"   (pass: dY > -{HOLD_DY:g} and |dX| < {HOLD_DX:g})")
    if success:
        lines.append("*** SUCCESS: world Y > 16000 (summit) reached ***")
    if outcome is not None:
        lines.append(("*** HOLD COMPLETE %d/%d: HELD  retained gain %+.3f ***" % (hold_n, hold_n, outcome["gain"]))
                     if outcome["held"] else ("*** HOLD COMPLETE %d/%d: NOT HELD ***" % (hold_n, hold_n)))
    return "\n".join(lines)


HUD_JS = """(text, color) => {
  let d = document.getElementById('rl-hud');
  if (!d) {
    d = document.createElement('div'); d.id = 'rl-hud';
    d.style.cssText = 'position:fixed;top:8px;left:8px;z-index:2147483647;background:rgba(0,0,0,.8);color:#fff;' +
      'font:14px/1.4 Consolas,Menlo,monospace;padding:8px 12px;border-radius:6px;white-space:pre;pointer-events:none;' +
      'border-left:6px solid #888';
    document.body.appendChild(d);
    const s = document.getElementById('status'); if (s) s.style.display = 'none';
  }
  d.textContent = text; d.style.borderLeftColor = color; return true; }"""


def run(b, actions, hold, seed, noise, rng, hold_ticks, headed=False, speed=1.0, chunk=None, render_every=1,
        after_success=0, ending_speed=1.0, fastest_frames=None):
    """Replay once. Returns (summary dict, per-tick list of (tick, x, y)).

    chunk = ticks per step_commands call / rendered frame (headed; default = --speed rounded).
    render_every = render+HUD every N chunks (0 = never render; headed only). Rendering cadence
    affects the real renderer's collision state, so bit-exactness must be re-verified per cadence.
    after_success = keep stepping this many ticks past the win flag so the project's own ending
    scripts can run (viewing only). ending_speed = playback speed of that phase (headed only).
    """
    base_tick = b.reset(seed)["tick"]                        # the game runs 120 warm-up ticks inside reset
    if fastest_frames is not None:
        b.evaluate(f"({SET_FASTEST_JS})({int(fastest_frames)})")
    cmds, cid = [], 1
    for ax, ay in actions:
        if noise:
            import numpy as np
            ax, ay = float(np.clip(ax + rng.normal(0, noise), -128, 128)), float(np.clip(ay + rng.normal(0, noise), -128, 128))
        for _ in range(hold):
            cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
    total = base_tick + len(cmds) + (hold_ticks or 0) + (after_success or 0)
    ticks, state = [], {"last": None, "maxy": -1e9, "dead": False, "success": False}
    frame_ticks = (chunk or max(1, round(speed))) if headed else 2400
    frame_dt = frame_ticks / (30.0 * speed) if headed else 0.0       # the game runs at 30 ticks/s
    route_end = [None]; outcome = [None]; next_frame = [time.perf_counter()]; frame_i = [0]; last_applied = [None]

    def consume(trace, phase, hold_i=0, hold_n=None, dt=None):
        for s in trace:
            ticks.append((s["tick"], s["player_world_x"], s["player_world_y"]))
            state["maxy"] = max(state["maxy"], s["player_world_y"]); state["dead"] |= bool(s["dead"]); state["success"] |= bool(s["success"])
        if trace: state["last"] = trace[-1]
        if headed and trace:
            if render_every and frame_i[0] % render_every == 0:
                s = trace[-1]
                b.evaluate("window.research.render()")
                color = "#3c3" if (outcome[0] and outcome[0]["held"]) or state["success"] else ("#e44" if state["dead"] or outcome[0] else "#fc3")
                b.evaluate(f"({HUD_JS})({json.dumps(hud_text(seed, speed, s['tick'], total, phase, hold_i, (hold_ticks if hold_n is None else hold_n), s['player_world_x'], s['player_world_y'], state['maxy'], route_end[0], outcome[0], state['success']))}, {json.dumps(color)})")
            next_frame[0] += (frame_dt if dt is None else dt)
            delay = next_frame[0] - time.perf_counter()
            if delay > 0: time.sleep(delay)
            else: next_frame[0] = time.perf_counter()
        frame_i[0] += 1

    for i in range(0, len(cmds), frame_ticks):
        trace = b.step_commands(cmds[i:i + frame_ticks])
        if trace: last_applied[0] = cmds[i + len(trace) - 1]
        consume(trace, "ROUTE")
        if state["dead"] or state["success"]: break
    last = state["last"]
    out = {"seed": seed, "noise": noise, "ticks": last["tick"], "x": last["player_world_x"], "y": last["player_world_y"],
           "max_y": state["maxy"], "dead": state["dead"], "success": state["success"]}
    if after_success and state["success"] and not state["dead"]:
        # The harness normally stops at the win flag; keep stepping so the project's own ending
        # scripts (Win / SAVE TIME TO CLOUD / high-score table) can play. Viewing only.
        ax = last_applied[0]["x"] if last_applied[0] else 0.0
        ay = last_applied[0]["y"] if last_applied[0] else 0.0
        e_chunk = max(1, round(ending_speed)) if headed else 2400
        e_dt = e_chunk / (30.0 * ending_speed) if headed else 0.0
        next_frame[0] = time.perf_counter()
        done = 0
        while done < after_success and not state["dead"]:
            n = min(e_chunk, after_success - done)
            trace = b.step_commands([{"x": ax, "y": ay, "id": cid + done + j} for j in range(n)], after=True)
            if not trace: break
            consume(trace, "ENDING", done + len(trace), after_success, e_dt)
            done += len(trace)
        e = state["last"]
        out["ending_ticks"] = done
        out["ending_x"], out["ending_y"], out["ending_dead"] = e["player_world_x"], e["player_world_y"], state["dead"]
    if hold_ticks and not (state["dead"] or state["success"]):
        ax, ay = actions[-1]
        route_end[0] = (out["x"], out["y"])
        hs = None
        for k in range(0, hold_ticks, frame_ticks):
            n = min(frame_ticks, hold_ticks - k)
            hs = b.step_commands([{"x": ax, "y": ay, "id": cid + k + j} for j in range(n)])
            if k + n >= hold_ticks:                          # decide the verdict before the final HUD frame
                out["after_hold_y"] = hs[-1]["player_world_y"]; out["after_hold_x"] = hs[-1]["player_world_x"]
                out["held"] = (not hs[-1]["dead"]) and hs[-1]["player_world_y"] > out["y"] - HOLD_DY and abs(hs[-1]["player_world_x"] - out["x"]) < HOLD_DX
                outcome[0] = {"held": out["held"], "gain": hs[-1]["player_world_y"] - SPAWN_Y}
            consume(hs, "HOLD", k + n)
    return out, ticks


def write_trace(path, meta, seed, ticks):
    with open(path, "w") as f:
        f.write(json.dumps({"meta": {**meta, "seed": seed, "ticks": len(ticks)}}) + "\n")
        for t, x, y in ticks:
            f.write(json.dumps({"tick": t, "x": x, "y": y}) + "\n")


def load_trace(path):
    meta, rows = {}, {}
    for line in Path(path).read_text().splitlines():
        if not line.strip(): continue
        d = json.loads(line)
        if "meta" in d: meta = d["meta"]
        else: rows[d["tick"]] = (d["x"], d["y"])
    return meta, rows


def compare_traces(ref_rows, got_ticks, eps):
    """First tick where (x, y) differs: bit-exactly, and by more than eps; plus drift summary."""
    got = {t: (x, y) for t, x, y in got_ticks}
    first_exact = first_eps = None; max_dev = (0.0, None); differing = 0; common = 0
    for t in sorted(ref_rows):
        if t not in got: continue
        common += 1
        dx, dy = got[t][0] - ref_rows[t][0], got[t][1] - ref_rows[t][1]
        dev = max(abs(dx), abs(dy))
        if dev != 0.0:
            differing += 1
            if first_exact is None: first_exact = {"tick": t, "ref": ref_rows[t], "got": got[t], "dx": dx, "dy": dy}
            if dev > eps and first_eps is None: first_eps = {"tick": t, "ref": ref_rows[t], "got": got[t], "dx": dx, "dy": dy}
            if dev > max_dev[0]: max_dev = (dev, t)
    last_common = max((t for t in ref_rows if t in got), default=None)
    extra_local = len(got) - common                        # e.g. ending ticks past the reference's win tick
    verdict = ("BIT-EXACT" if first_exact is None and common == len(ref_rows) else
               "WITHIN-EPS (not bit-exact)" if first_eps is None and common else "DIVERGED")
    return {"verdict": verdict, "eps": eps, "ticks_reference": len(ref_rows), "ticks_local": len(got), "ticks_compared": common,
            "extra_local_ticks": extra_local, "reference_complete": common == len(ref_rows),
            "first_bit_difference": first_exact, "first_divergence_over_eps": first_eps,
            "differing_ticks": differing, "max_abs_deviation": max_dev[0], "max_abs_deviation_tick": max_dev[1],
            "final_tick_compared": last_common,
            "final_delta": None if last_common is None else [got[last_common][0] - ref_rows[last_common][0], got[last_common][1] - ref_rows[last_common][1]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("route"); ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--noise", type=float, nargs="+", default=[0.0], help="gaussian pointer noise std (open-loop robustness probe)")
    ap.add_argument("--trials", type=int, default=3, help="noisy trials per (seed, noise>0)")
    ap.add_argument("--hold-ticks", type=int, default=0); ap.add_argument("--screenshot", default=None)
    ap.add_argument("--headed", action="store_true", help="visible Chrome window with a HUD overlay")
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed in multiples of real time (headed only; game = 30 ticks/s)")
    ap.add_argument("--after-success", type=int, default=0, help="keep stepping this many ticks past the win flag (play the project's ending; viewing only)")
    ap.add_argument("--presentation", action=argparse.BooleanOptionalAction, default=None,
                    help="reproduce the title-screen presentation state (timer digits + win animation). Default: on with --after-success")
    ap.add_argument("--fastest-frames", type=int, default=None,
                    help="set the cloud fastest time (frames) before the win so the game shows its normal end title instead of world record")
    ap.add_argument("--ending-speed", type=float, default=1.0, help="playback speed for the after-success phase (headed only)")
    ap.add_argument("--chunk", type=int, default=None, help="ticks per rendered frame / step call (headed; default = round(--speed))")
    ap.add_argument("--render-every", type=int, default=1, help="render+HUD every N frames (headed; 0 = never render, diagnostics only)")
    ap.add_argument("--trace-out", default=None, help="write per-tick JSONL (tick, x, y) for noiseless runs")
    ap.add_argument("--compare-trace", default=None, help="reference trace JSONL; report first divergence")
    ap.add_argument("--eps", type=float, default=1e-6, help="divergence threshold (world units) for --compare-trace")
    ap.add_argument("--report-out", default="divergence_report.json")
    ap.add_argument("--linger", type=float, default=10.0, help="seconds to keep the headed window open at the end")
    a = ap.parse_args()
    if a.presentation is None:
        a.presentation = a.after_success > 0
    d = json.load(open(a.route))
    rng = None
    if any(a.noise):
        import numpy as np
        rng = np.random.default_rng(0)
    ref_meta, ref_rows = load_trace(a.compare_trace) if a.compare_trace else ({}, None)
    runs, reports, diverged = 0, [], False
    with FastBridge(headless=not a.headed, presentation=a.presentation) as b:
        meta = env_meta(b) if (a.trace_out or a.compare_trace or a.headed) else None
        traced = sum(1 for _ in a.seeds for nz in a.noise if nz == 0)
        for seed in a.seeds:
            for nz in a.noise:
                for t in range(1 if nz == 0 else a.trials):
                    out, ticks = run(b, d["actions"], d["hold"], seed, nz, rng, a.hold_ticks, a.headed and nz == 0, a.speed,
                                     a.chunk, a.render_every, a.after_success, a.ending_speed, a.fastest_frames)
                    print(json.dumps(out), flush=True)
                    if nz != 0: continue
                    final_line = (f"FINAL seed={seed} tick={out['ticks']} x={out['x']!r} y={out['y']!r} max_y={out['max_y']!r} "
                                  f"dead={out['dead']} success={out['success']} held={out.get('held')}")
                    ending_line = None
                    if out.get("ending_ticks") is not None:
                        ending_line = (f"ENDING seed={seed} ticks_after_success={out['ending_ticks']} "
                                       f"x={out['ending_x']!r} y={out['ending_y']!r} dead={out['ending_dead']}")
                    if a.headed or a.trace_out or a.compare_trace:
                        print(final_line, flush=True)
                        if ending_line: print(ending_line, flush=True)
                    if a.headed:                          # show FINAL (+ ending) in the window too (viewing only)
                        cur = b.evaluate("(document.getElementById('rl-hud')||{}).textContent || ''")
                        extra = chr(10).join(x for x in (final_line, ending_line) if x)
                        b.evaluate(f"({HUD_JS})({json.dumps(cur + chr(10) + extra)}, "
                                   f"{json.dumps('#3c3' if (out.get('held') or out['success']) else '#e44')})")
                    if a.trace_out:
                        p = Path(a.trace_out)
                        if traced > 1: p = p.with_name(f"{p.stem}.seed{seed}{p.suffix}")
                        write_trace(p, meta, seed, ticks); print("trace", p, flush=True)
                    if ref_rows is not None:
                        rep = compare_traces(ref_rows, ticks, a.eps); rep["seed"] = seed
                        reports.append(rep); diverged |= rep["verdict"] == "DIVERGED"
                        fd = rep["first_divergence_over_eps"]
                        print(f"COMPARE seed={seed}: {rep['verdict']}; first divergence > {a.eps:g}: "
                              + (f"tick {fd['tick']} (dx={fd['dx']:.3e}, dy={fd['dy']:.3e})" if fd else "none")
                              + f"; first bit difference: " + (str(rep['first_bit_difference']['tick']) if rep['first_bit_difference'] else "none")
                              + f"; extra local ticks: {rep['extra_local_ticks']}; final delta {rep['final_delta']}", flush=True)
        if a.screenshot:
            run(b, d["actions"], d["hold"], a.seeds[0], 0.0, rng, 0)
            b.evaluate("research.render()")
            if b.driver: b.driver.save_screenshot(a.screenshot)
            else:
                import base64
                Path(a.screenshot).write_bytes(base64.b64decode(b._cdp.call("Page.captureScreenshot", format="png")["data"]))
            print("screenshot", a.screenshot)
        if a.headed and a.linger > 0:
            print(f"replay finished; window stays open {a.linger:g}s", flush=True); time.sleep(a.linger)
    if ref_rows is not None:
        Path(a.report_out).write_text(json.dumps({"reference": {"path": a.compare_trace, "meta": ref_meta}, "local_meta": meta, "runs": reports}, indent=1))
        print("divergence report", a.report_out, flush=True)
        if diverged: sys.exit(3)


if __name__ == "__main__":
    main()
