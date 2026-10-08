"""Local CEM from a retained frontier state toward a goal box (e.g. a foothold across a gap).

The goal box is search guidance only (derived from the real-renderer terrain probe). Success is
judged by the same retained-state hold test as everywhere else: a retained state at least
--gain higher than the start. Legal actions only; 4-tick decisions; real game.

  python explore/cem_launch.py --share-dir explore/runs/e9_share --goal 1990 2110 5170 5330 \
      --start-index 0 --seed 1 --out explore/runs/e10_cem0
"""
import argparse, json, math, os, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge
from explore.goexplore import Archive, import_path, best_foreign, HOLD, replay_verify


def knots_to_actions(knots, horizon):
    k = len(knots)
    t = np.linspace(0, k - 1, horizon)
    x = np.interp(t, np.arange(k), knots[:, 0]); y = np.interp(t, np.arange(k), knots[:, 1])
    return np.clip(np.stack([x, y], 1), -128, 128)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--share-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--goal", type=float, nargs=4, required=True, metavar=("X0", "X1", "Y0", "Y1"))
    ap.add_argument("--start-index", type=int, default=0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--horizon", type=int, default=48); ap.add_argument("--knot-every", type=int, default=4)
    ap.add_argument("--pop", type=int, default=128); ap.add_argument("--elite", type=int, default=16)
    ap.add_argument("--iters", type=int, default=15); ap.add_argument("--gain", type=float, default=40)
    ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    ap.add_argument("--secs", type=float, default=240)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    goal = {"x0": a.goal[0], "x1": a.goal[1], "y0": a.goal[2], "y1": a.goal[3]}
    log = []
    t0 = time.time()
    with FastBridge(headless=True) as b:
        b.reset(0)
        root = b.seed_cell(a.cx, a.cy)
        arch = Archive()
        arch.cell_node[root["key"]] = 0
        arch.info[0] = {"key": root["key"], "snap": root["snap"], "tick": root["tick"], "x": root["x"], "y": root["y"], "chosen": 0, "retained": True}
        fb = best_foreign(a.share_dir, -1)
        got = import_path(b, arch, root["snap"], fb, a.cx, a.cy)
        fy = got[1]["y"]
        starts = sorted([i for i in arch.cell_node.values() if arch.info[i]["retained"] and i != 0 and arch.info[i]["y"] >= fy - 25],
                        key=lambda i: arch.info[i]["x"])
        sid = starts[a.start_index % len(starts)]
        e = arch.info[sid]
        print(f"start node {sid}: x={e['x']:.1f} y={e['y']:.1f} (frontier y {fy:.1f}; {len(starts)} frontier candidates)", flush=True)
        K = a.horizon // a.knot_every + 1
        mean = np.zeros((K, 2)); std = np.full((K, 2), 70.0)
        best_overall = (math.inf, None)
        success = None
        for it in range(a.iters):
            if time.time() - t0 > a.secs: break
            knots = np.clip(rng.normal(mean, std, size=(a.pop, K, 2)), -128, 128)
            if it == 0: knots[0] = mean
            acts = [knots_to_actions(k, a.horizon) for k in knots]
            res = []
            for i in range(0, a.pop, 64):
                res += b.rollout_batch(e["snap"], [x.tolist() for x in acts[i:i + 64]], HOLD, goal)
            res = np.array(res)                                     # minD, x, y, dead, maxY, ticks
            fit = -res[:, 0] - 50 * res[:, 3]
            order = np.argsort(fit)[::-1]
            elites = knots[order[:a.elite]]
            mean = 0.3 * mean + 0.7 * elites.mean(0); std = np.maximum(0.3 * std + 0.7 * elites.std(0), 8.0)
            top = order[0]
            if res[top, 0] < best_overall[0]: best_overall = (res[top, 0], acts[top].tolist())
            rec = {"iter": it, "best_minD": float(res[top, 0]), "elite_mean_minD": float(res[order[:a.elite], 0].mean()),
                   "best_end": [float(res[top, 1]), float(res[top, 2])], "best_maxY": float(res[top, 4]),
                   "dead_frac": float(res[:, 3].mean()), "t": round(time.time() - t0, 1)}
            log.append(rec); print(json.dumps(rec), flush=True)
            # confirm with the real retained-state machinery on the top few
            for ci in order[:3]:
                r = b.explore_segment(e["snap"], acts[ci].tolist(), HOLD, a.cx, a.cy, {"testAll": True, "every": 1})
                good = [c for c in r["found"] if c["retained"] and c["y"] >= e["y"] + a.gain]
                if good:
                    c = max(good, key=lambda c: c["y"]); success = (acts[ci][:c["d"]].tolist(), c); break
            if success: break
        summary = {"args": vars(a), "start": {"node": sid, "x": e["x"], "y": e["y"]}, "iters": len(log), "elapsed_s": round(time.time() - t0, 1),
                   "best_minD": best_overall[0], "success": bool(success)}
        if success:
            acts_s, c = success
            full = arch.path(sid) + acts_s
            summary["success_state"] = {"x": c["x"], "y": c["y"], "d": c["d"]}
            summary["replay_verify"] = replay_verify(b, full, (c["x"], c["y"]))
            seed_tag = 9000 + a.seed
            (out / "path.json").write_text(json.dumps({"seed": seed_tag, "y": c["y"], "x": c["x"], "hold": HOLD, "actions": full}))
            if summary["replay_verify"]["match"] and summary["replay_verify"]["held"]:
                tmp = Path(a.share_dir) / f".best_{seed_tag}.tmp"
                tmp.write_text((out / "path.json").read_text()); os.replace(tmp, Path(a.share_dir) / f"best_{seed_tag}.json")
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        (out / "log.json").write_text(json.dumps(log))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
