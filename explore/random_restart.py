"""Baseline: random search with snapshot restarts (no cell archive, no potential).

Hill-climbs a single elite trajectory: from the best known exact snapshot, try a random pointer segment
(same generator as Go-Explore), keep the new state only if its *retained* height beats the elite, and
restart from spawn after `--restart-s` seconds without an improvement. Same action interface, same
retained (pointer-frozen) hold test, same bounded budget as the Go-Explore runs it is compared against.

  python explore/random_restart.py --secs 300 --seed 4100 --out explore/runs/b_rr_s4100
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge
from explore.goexplore import HOLD, gen_segment


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=float, default=300); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    ap.add_argument("--min-len", type=int, default=6); ap.add_argument("--max-len", type=int, default=30)
    ap.add_argument("--restart-s", type=float, default=60.0, help="restart from spawn after this long without improvement")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    t0 = time.time(); last_log = t0; last_improve = t0
    stats = {"segments": 0, "ticks": 0, "restarts": 0, "improvements": 0, "hold_tests": 0}
    with FastBridge(headless=True) as b:
        b.reset(0)
        root = b.seed_cell(a.cx, a.cy)
        elite = {"snap": root["snap"], "x": root["x"], "y": root["y"], "path": [], "decisions": 0}
        ymax_any = root["y"]
        while time.time() - t0 < a.secs:
            seg_len = int(rng.integers(a.min_len, a.max_len + 1))
            acts = gen_segment(rng, seg_len)
            r = b.explore_segment(elite["snap"], acts, HOLD, a.cx, a.cy, {})
            stats["segments"] += 1; stats["ticks"] += r["decisions"] * HOLD + r["holdTests"] * 90
            stats["hold_tests"] += r["holdTests"]
            ymax_any = max(ymax_any, r["maxY"])
            cells = [c for c in r["found"] if c["retained"]]
            best = max(cells, key=lambda c: c["y"], default=None)
            if best is not None and best["y"] > elite["y"] + 0.5:
                b.drop_snapshot(elite["snap"])
                elite = {"snap": best["snap"], "x": best["x"], "y": best["y"], "path": elite["path"] + acts[:best["d"]],
                         "decisions": elite["decisions"] + best["d"]}
                stats["improvements"] += 1; last_improve = time.time()
            if time.time() - last_improve > a.restart_s:          # random restart from spawn
                if elite["snap"] != root["snap"]: b.drop_snapshot(elite["snap"])
                root = b.seed_cell(a.cx, a.cy)
                elite = {"snap": root["snap"], "x": root["x"], "y": root["y"], "path": [], "decisions": 0}
                stats["restarts"] += 1; last_improve = time.time()
            if time.time() - last_log > 15:
                last_log = time.time()
                print(f"[{last_log - t0:6.0f}s] seg={stats['segments']} ticks/s={stats['ticks'] / (last_log - t0):.0f} "
                      f"elite_y={elite['y']:.1f} maxY_any={ymax_any:.0f} restarts={stats['restarts']} "
                      f"improvements={stats['improvements']} holdTests={stats['hold_tests']}", flush=True)
        el = time.time() - t0
        summary = {"args": vars(a), "elapsed_s": round(el, 1), "segments": stats["segments"], "ticks": stats["ticks"],
                   "ticks_per_s": round(stats["ticks"] / el), "restarts": stats["restarts"], "improvements": stats["improvements"],
                   "hold_tests": stats["hold_tests"], "maxY_any": ymax_any, "maxRetainedY": elite["y"],
                   "best_xy": [elite["x"], elite["y"]], "best_path_decisions": elite["decisions"], "success": False}
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        (out / "best_path.json").write_text(json.dumps({"hold": HOLD, "actions": elite["path"]}))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
