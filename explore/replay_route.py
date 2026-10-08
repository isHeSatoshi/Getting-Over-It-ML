"""Replay a saved route on the real compiled game from ordinary spawn and report where it ends.

The route is a list of pointer offsets in [-128,128]^2, each held for `hold` (4) ticks: exactly the
policy action interface. No snapshots are involved; this is a fresh reset + straight replay.

  python explore/replay_route.py explore/runs/e14_best_9341.json --seeds 0 1 2 3 --noise 0 0.5 2 --hold-ticks 180
  python explore/replay_route.py ROUTE.json --screenshot out.png
"""
import argparse, json, sys
import numpy as np
from research.fast_bridge import FastBridge


def run(b, actions, hold, seed, noise, rng, hold_ticks):
    b.reset(seed)
    cmds, cid = [], 1
    for ax, ay in actions:
        if noise:
            ax, ay = float(np.clip(ax + rng.normal(0, noise), -128, 128)), float(np.clip(ay + rng.normal(0, noise), -128, 128))
        for _ in range(hold):
            cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
    last, maxy, dead, success = None, -1e9, False, False
    for i in range(0, len(cmds), 2400):
        tr = b.step_commands(cmds[i:i + 2400])
        for s in tr:
            maxy = max(maxy, s["player_world_y"]); dead |= bool(s["dead"]); success |= bool(s["success"])
        if tr: last = tr[-1]
        if dead or success: break
    out = {"seed": seed, "noise": noise, "ticks": last["tick"], "x": last["player_world_x"], "y": last["player_world_y"],
           "max_y": maxy, "dead": dead, "success": success}
    if hold_ticks and not (dead or success):
        ax, ay = actions[-1]
        h = b.step_commands([{"x": ax, "y": ay, "id": cid + k} for k in range(hold_ticks)])
        out["after_hold_y"] = h[-1]["player_world_y"]; out["after_hold_x"] = h[-1]["player_world_x"]
        out["held"] = (not h[-1]["dead"]) and h[-1]["player_world_y"] > out["y"] - 6 and abs(h[-1]["player_world_x"] - out["x"]) < 12
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("route"); ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--noise", type=float, nargs="+", default=[0.0], help="gaussian pointer noise std (open-loop robustness probe)")
    ap.add_argument("--trials", type=int, default=3, help="noisy trials per (seed, noise>0)")
    ap.add_argument("--hold-ticks", type=int, default=0); ap.add_argument("--screenshot", default=None)
    a = ap.parse_args()
    d = json.load(open(a.route)); rng = np.random.default_rng(0)
    with FastBridge(headless=True) as b:
        for seed in a.seeds:
            for nz in a.noise:
                for t in range(1 if nz == 0 else a.trials):
                    print(json.dumps(run(b, d["actions"], d["hold"], seed, nz, rng, a.hold_ticks)), flush=True)
        if a.screenshot:
            run(b, d["actions"], d["hold"], a.seeds[0], 0.0, rng, 0)
            b.evaluate("research.render()"); b.driver.save_screenshot(a.screenshot); print("screenshot", a.screenshot)


if __name__ == "__main__":
    main()
