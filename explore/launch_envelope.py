"""Micro-experiment: from one retained frontier state, how far/high do random launches get,
per primitive family? Real game rollouts (rollout_batch), no learning.

  python explore/launch_envelope.py --share-dir DIR --goal X0 X1 Y0 Y1 --n 2000 --seed 1 --out FILE
"""
import argparse, json, math, time
import numpy as np
from research.fast_bridge import FastBridge
from explore.goexplore import Archive, import_path, best_foreign, gen_segment, HOLD

ap = argparse.ArgumentParser()
ap.add_argument("--share-dir", required=True); ap.add_argument("--goal", type=float, nargs=4, required=True)
ap.add_argument("--n", type=int, default=2000); ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--len", type=int, default=40); ap.add_argument("--out", required=True)
a = ap.parse_args()
rng = np.random.default_rng(a.seed); goal = dict(zip(("x0", "x1", "y0", "y1"), a.goal))
cx, cy = 16, 8
with FastBridge(headless=True) as b:
    b.reset(0); root = b.seed_cell(cx, cy)
    arch = Archive(); arch.cell_node[root["key"]] = 0
    arch.info[0] = {"key": root["key"], "snap": root["snap"], "tick": root["tick"], "x": root["x"], "y": root["y"], "chosen": 0, "retained": True}
    got = import_path(b, arch, root["snap"], best_foreign(a.share_dir, -1), cx, cy)
    fy = got[1]["y"]; sid = max((i for i in arch.cell_node.values() if arch.info[i]["retained"] and arch.info[i]["y"] >= fy - 25), key=lambda i: arch.info[i]["y"])
    e = arch.info[sid]; print(f"start y={e['y']:.1f} x={e['x']:.1f}", flush=True)
    result = {"start": [e["x"], e["y"]], "families": {}}
    for fam, use_spin in (("old_primitives", False), ("with_spin_release", True)):
        cands = []
        for _ in range(a.n):
            seg = gen_segment(rng, a.len, use_spin=use_spin)
            if use_spin is True and len(seg) < a.len: seg += [seg[-1]] * (a.len - len(seg))
            cands.append(seg[:a.len])
        t0 = time.time(); res = []
        for i in range(0, a.n, 256): res += b.rollout_batch(e["snap"], cands[i:i + 256], HOLD, goal)
        res = np.array(res); gain = res[:, 4] - e["y"]
        result["families"][fam] = {"n": a.n, "secs": round(time.time() - t0, 1),
            "apex_gain_max": float(gain.max()), "apex_gain_p99": float(np.percentile(gain, 99)), "apex_gain_p90": float(np.percentile(gain, 90)),
            "minD_min": float(res[:, 0].min()), "minD_p1": float(np.percentile(res[:, 0], 1)), "minD_p10": float(np.percentile(res[:, 0], 10)),
            "frac_dead": float(res[:, 3].mean()), "end_x_max": float(res[:, 1].max()), "end_x_min": float(res[:, 1].min())}
        print(fam, json.dumps(result["families"][fam]), flush=True)
    json.dump(result, open(a.out, "w"), indent=1)
