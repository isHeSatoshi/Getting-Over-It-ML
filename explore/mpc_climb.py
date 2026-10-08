"""Receding-horizon CEM ("MPC with an exact simulator") for sustained climbing from a saved route.

Each outer step: CEM over a short pointer plan (knot-interpolated, 4-tick decisions) from the current
exact snapshot. Every candidate ends with a held-pointer suffix (same length as the retained test), so
fitness = height after the hold = *retained* height, not transient flung height. The first --commit
decisions of the best plan are committed (legal action trace), then repeat. Search bookkeeping only;
the real game, exact in-page snapshots, final path re-verified by fresh reset + straight replay.

  python explore/mpc_climb.py --start explore/runs/e14_best_9341.json --seed 1 --secs 600 --out explore/runs/e15_mpc1
"""
import argparse, json, math, os, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge
from explore import goexplore as G

HOLD = G.HOLD
GOAL = {"x0": 0, "x1": 0, "y0": 0, "y1": 0}


def knots_to_actions(knots, horizon):
    k = len(knots); t = np.linspace(0, k - 1, horizon)
    return np.clip(np.stack([np.interp(t, np.arange(k), knots[:, 0]), np.interp(t, np.arange(k), knots[:, 1])], 1), -128, 128)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--secs", type=float, default=600)
    ap.add_argument("--horizon", type=int, default=24); ap.add_argument("--knot-every", type=int, default=4)
    ap.add_argument("--suffix", type=int, default=23, help="held-pointer decisions appended to each candidate (23*4 = 92 ticks)")
    ap.add_argument("--pop", type=int, default=64); ap.add_argument("--elite", type=int, default=8)
    ap.add_argument("--iters", type=int, default=3); ap.add_argument("--commit", type=int, default=8)
    ap.add_argument("--std", type=float, default=60.0); ap.add_argument("--stall-outer", type=int, default=40)
    ap.add_argument("--share-dir", default=None); ap.add_argument("--tag", type=int, default=0)
    ap.add_argument("--phi", action="store_true"); ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    if a.phi: G.load_phi()
    start = json.load(open(a.start)); base = [list(x) for x in start["actions"]]
    K = a.horizon // a.knot_every + 1
    t0 = time.time(); log = open(out / "log.jsonl", "w")
    with FastBridge(headless=True) as b:
        b.reset(0); root = b.seed_cell(a.cx, a.cy)
        r = b.explore_segment(root["snap"], base, HOLD, a.cx, a.cy, {"every": 100000, "testAll": True})
        S = b.snapshot(); cur = {"x": r["x"], "y": r["y"]}; path = list(base)
        print(f"start x={cur['x']:.1f} y={cur['y']:.1f} dead={r['dead']} decisions={len(path)}", flush=True)
        best = {"y": cur["y"], "path": list(path), "snap": S, "x": cur["x"]}
        mean = np.zeros((K, 2)); stuck = 0; outer = 0; last_pub = -1e9
        while time.time() - t0 < a.secs and stuck < a.stall_outer:
            outer += 1; std = np.full((K, 2), a.std)
            for it in range(a.iters):
                knots = np.clip(rng.normal(mean, std, size=(a.pop, K, 2)), -128, 128)
                if it == 0: knots[0] = mean
                plans = [np.concatenate([acts, np.repeat(acts[-1:], a.suffix, 0)]) for acts in (knots_to_actions(k, a.horizon) for k in knots)]
                res = []
                for i in range(0, a.pop, 64): res += b.rollout_batch(S, [p.tolist() for p in plans[i:i + 64]], HOLD, GOAL)
                res = np.array(res)                                     # minD, endX, endY, dead, maxY, ticks
                fit = res[:, 2] - 1000.0 * res[:, 3]
                order = np.argsort(fit)[::-1]; elites = knots[order[:a.elite]]
                mean = 0.4 * mean + 0.6 * elites.mean(0); std = np.maximum(0.4 * std + 0.6 * elites.std(0), 10.0)
            top = order[0]; plan = plans[top]
            r = b.explore_segment(S, plan[:a.commit].tolist(), HOLD, a.cx, a.cy, {"every": 100000, "testAll": False})
            S2 = b.snapshot(); path += [list(map(float, p)) for p in plan[:a.commit]]
            ok = b.rollout_batch(S2, [[list(map(float, plan[a.commit - 1]))] * a.suffix], HOLD, GOAL)[0]
            retained = (not ok[3]) and ok[2] > r["y"] - 6 and abs(ok[1] - r["x"]) < 12 and not r["dead"]
            if S != best["snap"]: b.drop_snapshot(S)
            if r["dead"]:
                b.drop_snapshot(S2); S = best["snap"]; path = list(best["path"]); mean[:] = 0; stuck += 1
                rec = {"outer": outer, "dead": True, "t": round(time.time() - t0, 1)}
            else:
                S = S2; cur = {"x": r["x"], "y": r["y"]}
                mean = np.concatenate([mean[1:], mean[-1:]])             # warm start
                if retained and cur["y"] > best["y"] + 0.5:
                    if best["snap"] != S: b.drop_snapshot(best["snap"])
                    best = {"y": cur["y"], "path": list(path), "snap": S, "x": cur["x"]}; stuck = 0
                else: stuck += 1
                rec = {"outer": outer, "x": round(cur["x"], 1), "y": round(cur["y"], 1), "pred_endY": round(float(res[top, 2]), 1),
                       "retained": bool(retained), "best_y": round(best["y"], 1), "stuck": stuck, "dead_frac": round(float(res[:, 3].mean()), 2), "t": round(time.time() - t0, 1)}
            log.write(json.dumps(rec) + "\n"); log.flush()
            if outer % 5 == 0: print(json.dumps(rec), flush=True)
            if a.share_dir and best["y"] > last_pub + 10:
                last_pub = best["y"]; prg = G.prog(best["x"], best["y"])
                tmp = Path(a.share_dir) / f".best_{a.tag}.tmp"; tmp.write_text(json.dumps({"seed": a.tag, "y": prg, "x": best["x"], "hold": HOLD, "actions": best["path"]}))
                os.replace(tmp, Path(a.share_dir) / f"best_{a.tag}.json")
        verify = G.replay_verify(b, best["path"], (best["x"], best["y"]))
        summary = {"args": vars(a), "elapsed_s": round(time.time() - t0, 1), "outer_steps": outer, "start_y": start.get("y"),
                   "best_xy": [best["x"], best["y"]], "decisions": len(best["path"]), "replay_verify": verify}
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        (out / "best_path.json").write_text(json.dumps({"hold": HOLD, "actions": best["path"]}))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
