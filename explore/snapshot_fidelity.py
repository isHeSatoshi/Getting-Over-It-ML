"""Falsification test: in-page snapshot/restore must reproduce straight-run traces exactly.

For each (prefix path, snapshot tick k, continuation C):
  A  = reset; prefix[:k]; snapshot; C                      (straight run)
  B  = diverge with D; restore; C                          (restore after drift)
  B2 = restore again; C                                    (restore is repeatable)
All numeric telemetry fields of every tick must be identical (zero error).
"""
import json, math, sys, time
import numpy as np
from research.fast_bridge import FastBridge

def circle(n, radius=90.0, period=120, sign=-1, start=0):
    return [(radius*math.cos(sign*(start+i)*2*math.pi/period), radius*math.sin(sign*(start+i)*2*math.pi/period)) for i in range(n)]

def walk(n, seed, scale=128.0, tau=25.0):
    rng = np.random.default_rng(seed); x = np.zeros(2); out = []
    for _ in range(n):
        x = x*(1-1/tau) + rng.normal(0, 0.35, 2)
        out.append(tuple(np.clip(x*scale*0.6, -128, 128)))
    return out

def cmds(points, first_id):
    return [{"x": float(x), "y": float(y), "id": first_id+i} for i, (x, y) in enumerate(points)]

def diff(a, b):
    """First differing tick and fields between two traces; None if identical."""
    if len(a) != len(b): return {"length": [len(a), len(b)]}
    for i, (sa, sb) in enumerate(zip(a, b)):
        bad = {k: [sa[k], sb.get(k)] for k in sa if sa[k] != sb.get(k)}
        if bad: return {"tick_index": i, "fields": dict(list(bad.items())[:6]), "nbad": len(bad)}
    return None

PREFIXES = {"circle": circle(400), "walk7": walk(400, 7), "walk11": walk(400, 11), "idle": [(0.0, 0.0)]*400}
KS = [0, 37, 150, 250, 399]
results, total, bad = [], 0, 0
t_snap, t_rest = [], []
with FastBridge(headless=True) as b:
    for name, path in PREFIXES.items():
        for k in KS:
            for cname, cont in (("walk", walk(300, 100+k)), ("circle", circle(300, 70, 90, +1, k))):
                b.reset(0)
                if k: b.step_commands(cmds(path[:k], 1))
                s_before = b.read_state()
                t0 = time.perf_counter(); h = b.snapshot(); t_snap.append(time.perf_counter()-t0)
                C = cmds(cont, k+1)
                A = b.step_commands(C)
                b.step_commands(cmds(circle(200, 100, 60, +1), 5000))        # diverge
                t0 = time.perf_counter(); st = b.restore(h); t_rest.append(time.perf_counter()-t0)
                restored_ok = (st == s_before)
                B = b.step_commands(C)
                b.restore(h)
                B2 = b.step_commands(C)
                d1, d2 = diff(A, B), diff(A, B2)
                total += 1
                ok = restored_ok and d1 is None and d2 is None
                bad += (not ok)
                rec = {"prefix": name, "k": k, "cont": cname, "restored_state_equal": restored_ok,
                       "A_vs_B": d1, "A_vs_B2": d2, "end": [round(A[-1]["player_world_x"],2), round(A[-1]["player_world_y"],2)],
                       "contacts_A": sum(1 for s in A if s["hammer_collision"] or s["body_collision"])}
                results.append(rec)
                print(("OK  " if ok else "FAIL"), name, k, cname, rec["end"], "contact ticks", rec["contacts_A"], "" if ok else json.dumps(rec)[:400], flush=True)
                b.drop_snapshot(h)
print(f"\ncases={total} failures={bad}  snapshot ms mean={1000*np.mean(t_snap):.2f}  restore ms mean={1000*np.mean(t_rest):.2f}")
json.dump(results, open("explore/snapshot_fidelity_result.json", "w"), indent=1)
sys.exit(1 if bad else 0)
