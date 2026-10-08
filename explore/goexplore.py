"""Bounded Go-Explore on the real compiled game using exact in-page snapshots.

Search runs at the policy's own interface: one pointer offset in [-128,128]^2 held for 4
ticks per decision. Every result is a legal action trace from ordinary spawn; the best path is
re-verified at the end with a fresh reset + straight replay (no snapshots involved).

  python explore/goexplore.py --secs 300 --seed 0 --out explore/runs/e3_seed0
"""
import argparse, glob, json, math, os, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge

HOLD = 4
PHI = None                                     # optional geometry potential (explore/potential.py); progress = -phi
_META = None
PHI_MAXX = float(os.environ.get('PHI_MAXX', '1e9'))   # cells right of this rank last (forbid returning to a known dead-end region)
PHI_MINY = float(os.environ.get('PHI_MINY', '-1e9'))   # cells below this height rank last (stage a search above a known staircase)


def load_phi():
    global PHI, _META
    PHI = np.load(f"explore/world/phi{os.environ.get('PHI_TAG', '')}.npy"); _META = json.load(open("explore/world/world_meta.json"))


def prog(x, y):
    """Search progress scalar: height, or -phi(x, y) when a potential is loaded."""
    if PHI is None: return y
    r = min(PHI.shape[0] - 1, max(0, int(round((_META["y1"] - y) / _META["unit"]))))
    c = min(PHI.shape[1] - 1, max(0, int(round((x - _META["x0"]) / _META["unit"]))))
    return -float(PHI[r, c]) - (1e5 if (y < PHI_MINY or x > PHI_MAXX) else 0.0)


def norm(cells):
    for c in cells:
        c["ry"] = c["y_raw"] = c["y"]; c["y"] = prog(c["x"], c["y"])
    return cells
LEDGE = (305.0, 335.0, 100.0, 112.0)          # first ledge box (X range, Y range)


def gen_spin_release(rng, total):
    """Spin the pointer around a circle (hammer propeller), then release in a held direction."""
    n1 = int(rng.integers(4, 25)); w = float(rng.choice([-1, 1])) * rng.uniform(0.35, 0.95)
    r = rng.uniform(100, 128); phi = rng.uniform(0, 2 * math.pi)
    out = [(r * math.cos(phi + w * i), r * math.sin(phi + w * i)) for i in range(n1)]
    end = phi + w * (n1 - 1); n2 = int(rng.integers(1, 11)); delta = rng.uniform(-math.pi, math.pi)
    r2 = float(rng.choice([128.0, r]))
    out += [(r2 * math.cos(end + delta), r2 * math.sin(end + delta))] * n2
    while len(out) < total: out.append(out[-1])
    return out[:max(total, n1 + n2)]


def gen_gait(rng, length, ha):
    """Climbing gait aligned to the hammer's current direction `ha` (rad): the pointer circles/rocks starting where the
    hammer already is, so there is no whip at the start. Climbing in the verified route is ~50 deg/decision circling at r~120."""
    r = rng.uniform(90, 128); w = float(rng.choice([-1, 1])) * rng.uniform(0.25, 1.0)
    th0 = ha + rng.uniform(-0.9, 0.9); n = int(rng.integers(8, max(9, length) + 1)); mode = int(rng.integers(0, 3))
    if mode == 2:                                           # rocking arc: back-and-forth around th0
        amp = rng.uniform(0.6, 2.2); out = [(r * math.cos(th0 + amp * math.sin(w * i)), r * math.sin(th0 + amp * math.sin(w * i))) for i in range(n)]
    else:
        out = [(r * math.cos(th0 + w * i), r * math.sin(th0 + w * i)) for i in range(n)]
        if mode == 1: out += [out[-1]] * int(rng.integers(3, 11))        # dwell: let the body settle on the last pointer
    return [[float(np.clip(x, -128, 128)), float(np.clip(y, -128, 128))] for x, y in out]


def gen_segment(rng, length, use_spin=True):
    kinds = ["waypoint", "circle", "walk", "push", "spin"] if use_spin else ["waypoint", "circle", "walk", "push"]
    p = [0.3, 0.2, 0.15, 0.05, 0.3] if use_spin else [0.4, 0.3, 0.2, 0.1]
    kind = rng.choice(kinds, p=p)
    out = []
    if kind == "spin":
        out = gen_spin_release(rng, length)
        return [[float(np.clip(x, -128, 128)), float(np.clip(y, -128, 128))] for x, y in out]
    if kind == "waypoint":
        while len(out) < length:
            r = rng.uniform(0.3, 1.0) * 128; phi = rng.uniform(0, 2 * math.pi)
            out += [(r * math.cos(phi), r * math.sin(phi))] * int(rng.integers(1, 7))
    elif kind == "circle":
        phi = rng.uniform(0, 2 * math.pi); w = rng.uniform(-0.9, 0.9); r = rng.uniform(50, 128)
        out = [(r * math.cos(phi + w * i), r * math.sin(phi + w * i)) for i in range(length)]
    elif kind == "walk":
        p = rng.uniform(-80, 80, 2)
        for _ in range(length):
            p = np.clip(p * 0.9 + rng.normal(0, 40, 2), -128, 128); out.append((p[0], p[1]))
    else:
        phi = rng.uniform(0, 2 * math.pi); out = [(128 * math.cos(phi), 128 * math.sin(phi))] * length
    return [[float(np.clip(x, -128, 128)), float(np.clip(y, -128, 128))] for x, y in out[:length]]


FRONT_SCALE = [40.0]
LOCAL = {"radius": 0.0}                         # if > 0: only pick cells within this real height of the best retained cell


class Archive:
    def __init__(self):
        self.nodes = {0: (None, [])}           # id -> (parent id, decisions from parent)
        self.cell_node = {}                     # cell key -> node id (current representative)
        self.info = {}                          # node id -> dict(key, snap, tick, x, y, chosen)
        self.next_id = 1

    def path(self, node_id):
        chain = []
        while node_id is not None:
            parent, actions = self.nodes[node_id]
            chain.append(actions); node_id = parent
        return [a for seg in reversed(chain) for a in seg]


def pick(archive, rng, stalled=False):
    """Tiers: steep retained frontier / route-wide retained (shallow height slope) / novelty only."""
    ids = list(archive.cell_node.values())
    chosen = np.array([archive.info[i]["chosen"] for i in ids], float)
    ys = np.array([archive.info[i]["y"] for i in ids], float)
    ret = np.array([archive.info[i]["retained"] for i in ids], bool)
    w = (chosen + 1.0) ** -0.5
    if LOCAL["radius"] > 0:
        ry = np.array([archive.info[i].get("ry", archive.info[i]["y"]) for i in ids], float)
        near = ry >= ry[ret].max() - LOCAL["radius"] if ret.any() else np.ones(len(ids), bool)
        if near.any(): w = w * near
    u = rng.random(); p_front, p_route, p_high = (0.4, 0.25, 0.15) if stalled else (0.35, 0.25, 0.1)
    if ret.any() and u < p_front:
        w = w * ret * np.exp((ys - ys[ret].max()) / FRONT_SCALE[0])
    elif ret.any() and u < p_front + p_route:
        w = w * ret * np.exp((ys - ys[ret].max()) / 800.0)
    elif u < p_front + p_route + p_high:                      # high non-retained (apex/sliding) states too
        w = w * np.exp((ys - ys.max()) / FRONT_SCALE[0])
    w = np.where(np.isfinite(w), w, 0.0)                      # degenerate tier (e.g. --local-radius left only
    total = float(w.sum())                                    # cells far below the global max): fall back to uniform
    if total <= 0.0:
        w = np.ones(len(ids), float); total = float(len(ids))
    return ids[int(rng.choice(len(ids), p=w / total))]


def replay_verify(bridge, actions, expect_xy):
    start = bridge.reset(0)
    cmds, cid = [], 1
    for ax, ay in actions:
        for _ in range(HOLD):
            cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
    last = start
    for i in range(0, len(cmds), 2400):
        tr = bridge.step_commands(cmds[i:i + 2400])
        if tr: last = tr[-1]
    end = {"x": last["player_world_x"], "y": last["player_world_y"], "tick": last["tick"],
           "match": abs(last["player_world_x"] - expect_xy[0]) < 1e-9 and abs(last["player_world_y"] - expect_xy[1]) < 1e-9}
    ax, ay = actions[-1]
    hold = bridge.step_commands([{"x": ax, "y": ay, "id": cid + i} for i in range(180)])
    end["after_180tick_hold_xy"] = [hold[-1]["player_world_x"], hold[-1]["player_world_y"]]
    end["min_y_during_hold"] = min(h["player_world_y"] for h in hold)
    end["held"] = (not hold[-1]["dead"]) and hold[-1]["player_world_y"] > end["y"] - 6 and abs(hold[-1]["player_world_x"] - end["x"]) < 12
    return end


def publish(share, seed, y, x, path):
    tmp = Path(share) / f".best_{seed}.tmp"
    tmp.write_text(json.dumps({"seed": seed, "y": y, "x": x, "hold": HOLD, "actions": path}))
    os.replace(tmp, Path(share) / f"best_{seed}.json")


def best_foreign(share, seed, rng=None, near=60.0):
    """Best foreign path; with rng, a random one within `near` of the best (island diversity)."""
    found = []
    for f in glob.glob(str(Path(share) / "best_*.json")):
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            continue
        if d["seed"] != seed: found.append(d)
    if not found: return None
    top = max(d["y"] for d in found)
    if rng is None: return max(found, key=lambda d: d["y"])
    close = [d for d in found if d["y"] >= top - near]
    return close[int(rng.integers(len(close)))]


def import_path(b, arch, root_snap, d, cx, cy, every=6):
    """Materialise another island's path as a route: replay from the root snapshot, hold-testing
    every `every` decisions and registering those states (retained or not) as branch points."""
    r = b.explore_segment(root_snap, d["actions"], HOLD, cx, cy, {"every": every, "testAll": True}); norm(r["found"])
    last = None
    for c in r["found"]:
        nid = arch.next_id; arch.next_id += 1
        arch.nodes[nid] = (0, d["actions"][:c["d"]])
        old = arch.cell_node.get(c["key"])
        if old is not None: arch.info[old]["snap"] = None
        arch.cell_node[c["key"]] = nid
        arch.info[nid] = {"key": c["key"], "snap": c["snap"], "tick": c["tick"], "x": c["x"], "y": c["y"], "ry": c["ry"], "chosen": 0, "retained": bool(c["retained"]), "ha": math.atan2(c["hy"] - c["y_raw"], c["hx"] - c["x"])}
        if c["retained"] and (last is None or c["y"] >= arch.info[last]["y"]): last = nid
    if last is None: return None
    return last, {"y": arch.info[last]["y"], "n": len(r["found"]), "retained": sum(1 for c in r["found"] if c["retained"])}


def prune(b, arch, max_cells):
    if len(arch.cell_node) <= max_cells: return 0
    cand = [(arch.info[i]["y"], k, i) for k, i in arch.cell_node.items() if not arch.info[i]["retained"] and arch.info[i]["chosen"] >= 1]
    cand.sort()
    n = 0
    for _, k, i in cand[:max(1, len(arch.cell_node) - int(max_cells * 0.8))]:
        if arch.info[i]["snap"] is not None: b.drop_snapshot(arch.info[i]["snap"])
        arch.info[i]["snap"] = None; del arch.cell_node[k]; n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=float, default=300); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    ap.add_argument("--min-len", type=int, default=6); ap.add_argument("--max-len", type=int, default=30)
    ap.add_argument("--max-cells", type=int, default=60000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--share-dir", default=None); ap.add_argument("--sync-s", type=float, default=20)
    ap.add_argument("--import-margin", type=float, default=30)
    ap.add_argument("--stall-s", type=float, default=0, help="stop if retained Y does not improve for this long (0=off)")
    ap.add_argument("--phi", action="store_true", help="progress = -phi (offline geometry potential) instead of height")
    ap.add_argument("--phi-margin", type=float, default=150); ap.add_argument("--front-scale", type=float, default=40)
    ap.add_argument("--gait-frac", type=float, default=0.0, help="fraction of segments from the hammer-aligned gait generator")
    ap.add_argument("--local-radius", type=float, default=0.0, help="restrict picks to cells within this height of the best retained cell")
    ap.add_argument("--heap-mb", type=float, default=600, help="prune stored cells above this JS heap size")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    arch = Archive(); t0 = time.time(); last_log = t0; last_sync = t0 - a.sync_s; published_y = -1e9; imports = 0; last_improve = t0
    if a.share_dir: Path(a.share_dir).mkdir(parents=True, exist_ok=True)
    stats = {"segments": 0, "ticks": 0, "hold_tests": 0, "ledge_first_s": None, "success": False}
    nodes_log = (out / "nodes.jsonl").open("w")
    if a.phi: load_phi()
    FRONT_SCALE[0] = a.front_scale; LOCAL["radius"] = a.local_radius
    with FastBridge(headless=True) as b:
        b.reset(0)
        if a.phi:
            g = np.load(f"explore/world/phi_x4{os.environ.get('PHI_TAG', '')}.npy")
            b.set_phi(g.shape[1], g.shape[0], _META["x0"], _META["y1"], _META["unit"] * 4, [round(float(v), 1) for v in g.ravel()])
        root = b.seed_cell(a.cx, a.cy); norm([root])
        arch.cell_node[root["key"]] = 0
        arch.info[0] = {"key": root["key"], "snap": root["snap"], "tick": root["tick"], "x": root["x"], "y": root["y"], "ry": root["ry"], "chosen": 0, "retained": True, "ha": math.atan2(root["hy"] - root["y_raw"], root["hx"] - root["x"])}
        ymax, xmax_hi, best_node, rymax = root["ry"], 0.0, 0, root["y"]
        while time.time() - t0 < a.secs and not stats["success"] and not (a.stall_s and time.time() - last_improve > a.stall_s):
            stalled_for = time.time() - last_improve
            nid = pick(arch, rng, stalled_for > 90); e = arch.info[nid]; e["chosen"] += 1
            seg_len = int(rng.integers(a.min_len, (a.max_len * 2 if stalled_for > 90 else a.max_len) + 1))
            acts = gen_gait(rng, seg_len, e["ha"]) if (a.gait_frac and rng.random() < a.gait_frac) else gen_segment(rng, seg_len)
            r = b.explore_segment(e["snap"], acts, HOLD, a.cx, a.cy, {"phiMargin": a.phi_margin}); norm(r["found"])
            stats["segments"] += 1; stats["ticks"] += r["decisions"] * HOLD + r["holdTests"] * 90; stats["hold_tests"] += r["holdTests"]
            for c in r["found"]:
                if len(arch.cell_node) >= a.max_cells and c["key"] not in arch.cell_node: continue
                new_id = arch.next_id; arch.next_id += 1
                seg = acts[:c["d"]]
                arch.nodes[new_id] = (nid, seg)
                nodes_log.write(json.dumps({"id": new_id, "parent": nid, "actions": seg, "x": c["x"], "y": c["ry"], "tick": c["tick"]}) + "\n")
                old = arch.cell_node.get(c["key"])
                if old is not None: arch.info[old]["snap"] = None
                arch.cell_node[c["key"]] = new_id
                arch.info[new_id] = {"key": c["key"], "snap": c["snap"], "tick": c["tick"], "x": c["x"], "y": c["y"], "ry": c["ry"], "chosen": 0, "retained": bool(c["retained"]), "ha": math.atan2(c["hy"] - c["y_raw"], c["hx"] - c["x"])}
                if c["ry"] > ymax: ymax = c["ry"]
                if c["retained"] and c["y"] > rymax: rymax, best_node, last_improve = c["y"], new_id, time.time()
                if c["retained"] and LEDGE[0] <= c["x"] <= LEDGE[1] and LEDGE[2] <= c["ry"] <= LEDGE[3] and stats["ledge_first_s"] is None:
                    stats["ledge_first_s"] = round(time.time() - t0, 1); stats["ledge_node"] = new_id
                if c["x"] > xmax_hi and c["ry"] >= 90: xmax_hi = c["x"]
            stats["success"] = bool(r["success"])
            if stats["success"]:
                stats["success_actions"] = arch.path(nid) + acts[:r["decisions"]]
            if a.share_dir and time.time() - last_sync > a.sync_s:
                last_sync = time.time()
                if rymax > published_y + 1e-9:
                    publish(a.share_dir, a.seed, rymax, arch.info[best_node]["x"], arch.path(best_node)); published_y = rymax
                fb = best_foreign(a.share_dir, a.seed, rng)
                if fb and fb["y"] > rymax + a.import_margin:
                    got = import_path(b, arch, arch.info[0]["snap"], fb, a.cx, a.cy)
                    if got:
                        imports += 1; rymax = max(rymax, got[1]["y"]); best_node = got[0]; last_improve = time.time()
                        print(f"  import from seed {fb['seed']}: y={fb['y']:.1f} (path {len(fb['actions'])} decisions; {got[1]['n']} route cells, {got[1]['retained']} retained)", flush=True)
                if len(arch.cell_node) > a.max_cells: prune(b, arch, a.max_cells)
            if time.time() - last_log > 15:
                last_log = time.time(); el = last_log - t0
                heap = b.evaluate("Math.round((performance.memory||{}).usedJSHeapSize/1e6)")
                if heap and heap > a.heap_mb:
                    pruned = prune(b, arch, int(len(arch.cell_node) * 0.625)); print(f"  heap {heap}MB > {a.heap_mb}: pruned {pruned} cells", flush=True)
                print(f"[{el:6.0f}s] cells={len(arch.cell_node)} seg={stats['segments']} ticks/s={stats['ticks']/el:.0f} "
                      f"maxY(any)={ymax:.0f} maxRetainedProg={rymax:.1f} bestXY=({arch.info[best_node]['x']:.0f},{arch.info[best_node]['ry']:.0f}) maxX(y>=90)={xmax_hi:.0f} ledgeHeld_first={stats['ledge_first_s']} holdTests={stats['hold_tests']} heapMB={heap}", flush=True)
        nodes_log.close()
        el = time.time() - t0
        bn = best_node
        verify = None if stats["success"] else replay_verify(b, arch.path(bn), (arch.info[bn]["x"], arch.info[bn]["ry"]))   # a success run is verified by explore/replay_route.py on SUCCESS_path.json
        summary = {"args": vars(a), "elapsed_s": round(el, 1), "cells": len(arch.cell_node), "segments": stats["segments"],
                   "ticks": stats["ticks"], "ticks_per_s": round(stats["ticks"] / el), "maxY_any": ymax, "maxRetainedY": rymax, "retained_cells": sum(1 for i in arch.cell_node.values() if arch.info[i]["retained"]), "hold_tests": stats["hold_tests"], "imports": imports, "stalled": bool(a.stall_s and time.time() - last_improve > a.stall_s), "maxX_y90": xmax_hi,
                   "ledge_first_s": stats["ledge_first_s"], "success": stats["success"],
                   "best_node": bn, "best_xy": [arch.info[bn]["x"], arch.info[bn]["ry"]], "best_progress": arch.info[bn]["y"], "best_path_decisions": len(arch.path(bn)),
                   "best_replay_verify": verify}
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        (out / "best_path.json").write_text(json.dumps({"hold": HOLD, "actions": arch.path(bn)}))
        if stats["success"]:
            (out / "SUCCESS_path.json").write_text(json.dumps({"hold": HOLD, "actions": stats["success_actions"]}))
        if stats.get("ledge_node") is not None:
            (out / "ledge_path.json").write_text(json.dumps({"hold": HOLD, "actions": arch.path(stats["ledge_node"])}))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
