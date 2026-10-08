"""Closed-loop trajectory-tracking policy for the verified route (feedback, not open loop).

The open-loop trace dies under any pointer perturbation (noise std 0.01 already breaks it). This turns
it into a feedback policy: a saved route is treated as a *reference* (position at every tick), and at
every decision the controller compares the state the game is actually in with the reference, replans a
short pointer plan with the real game as the simulator, and commits the first few decisions. When the
state is on the reference (the usual case) it applies the reference action directly, so a clean run is
bit-exact and costs nothing extra.

This is trajectory tracking, not a standalone learned policy: it needs the reference route. What it adds
is what the open-loop trace lacks - it corrects deviations instead of following them.

  python explore/policy_track.py --route explore/runs/e28_SUCCESS_s3100.json --seeds 0 1 2 3 --noise 0
  python explore/policy_track.py --route explore/runs/e28_SUCCESS_s3100.json --seeds 0 1 --noise 0.25 1.0
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge

HOLD = 4
TOL = 0.5          # deviation (world units) below which the reference action is applied unchanged


def load_reference(path):
    """Reference trace JSONL -> (sorted ticks, x array, y array)."""
    ref = {}
    for line in Path(path).read_text().splitlines():
        d = json.loads(line)
        if "tick" in d: ref[int(d["tick"])] = (float(d["x"]), float(d["y"]))
    ticks = np.array(sorted(ref), dtype=np.int64)
    xs = np.array([ref[t][0] for t in ticks]); ys = np.array([ref[t][1] for t in ticks])
    return ticks, xs, ys


class PhaseTracker:
    """Estimate which point of the reference the game is at.

    A controller that only compares against the reference at the current tick loses the reference the
    moment it deviates (the reference races ahead in ticks while the body is stuck). This matches the
    current position against a window of reference points instead and moves the window forward
    monotonically, which is the standard way to follow a trajectory after a large deviation.
    """

    def __init__(self, ticks, xs, ys, window=240, min_advance=0):
        self.ticks, self.xs, self.ys = ticks, xs, ys
        self.window, self.min_advance = window, min_advance
        self.i = 0

    def sync(self, x, y, tick):
        lo = self.i
        hi = min(len(self.ticks) - 1, self.i + self.window)
        d = np.hypot(self.xs[lo:hi + 1] - x, self.ys[lo:hi + 1] - y)
        j = lo + int(np.argmin(d))
        self.i = max(self.i + self.min_advance, j)
        return self.i

    def at(self, i):
        i = min(len(self.ticks) - 1, max(0, i))
        return self.ticks[i], self.xs[i], self.ys[i]

    def pos_at_index(self, i):
        i = min(len(self.ticks) - 1, max(0, i))
        return float(self.xs[i]), float(self.ys[i])

    def tick_at_index(self, i):
        return int(self.ticks[min(len(self.ticks) - 1, max(0, i))])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--route", default="explore/runs/e28_SUCCESS_s3100.json")
    ap.add_argument("--reference", default="explore/reference/e28_success_16001.trace.jsonl")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--noise", type=float, nargs="+", default=[0.0], help="gaussian pointer noise std added to the applied action")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--horizon", type=int, default=12); ap.add_argument("--commit", type=int, default=4)
    ap.add_argument("--pop", type=int, default=24); ap.add_argument("--iters", type=int, default=2)
    ap.add_argument("--elite", type=int, default=6); ap.add_argument("--std", type=float, default=40.0)
    ap.add_argument("--tol", type=float, default=TOL, help="apply the reference action unchanged below this deviation")
    ap.add_argument("--window", type=int, default=240, help="how far ahead of the phase estimate to search when re-synchronising")
    ap.add_argument("--out", default="explore/runs/p_track")
    ap.add_argument("--trace-out", default=None)
    ap.add_argument("--max-decisions", type=int, default=0, help="0 = all")
    ap.add_argument("--no-resync", action="store_true",
                    help="compare against the reference at the current tick (loses the reference after a large deviation)")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    route = json.loads(Path(a.route).read_text()); actions = route["actions"]; hold = int(route.get("hold", HOLD))
    ticks, rxs, rys = load_reference(a.reference)
    ref_at_tick = dict(zip(ticks.tolist(), zip(rxs.tolist(), rys.tolist())))
    rows = []
    with FastBridge(headless=True) as b:
        for noise in a.noise:
            for seed in a.seeds:
                for trial in range(a.trials if noise > 0 else 1):
                    rng = np.random.default_rng(1000 * seed + trial)
                    b.reset(seed)
                    base = b.evaluate("window.research.state()")["tick"]      # warm-up ticks inside reset
                    tracker = PhaseTracker(ticks, rxs, rys, window=a.window)
                    stats = {"replans": 0, "reference": 0, "max_dev": 0.0, "dev_sum": 0.0, "dev_n": 0, "resyncs": 0}
                    cid = 1; i = 0; dead = success = False; t0 = time.time()
                    while i < len(actions) and not dead and not success:
                        st = b.evaluate("window.research.state()")
                        tick = st["tick"]
                        x, y = st["player_world_x"], st["player_world_y"]
                        rx, ry = ref_at_tick.get(tick, (x, y))
                        if a.no_resync:
                            idx = None
                        else:
                            before = tracker.i
                            idx = tracker.sync(x, y, tick)      # phase estimate: used for re-plan targets only
                            if idx > before: stats["resyncs"] += 1
                        dev = math.hypot(x - rx, y - ry)
                        stats["max_dev"] = max(stats["max_dev"], dev); stats["dev_sum"] += dev; stats["dev_n"] += 1
                        n = 1
                        if dev <= a.tol:
                            # On reference: apply the reference action for this decision. The action index is
                            # the decisions actually applied (not the phase estimate), so a clean run stays
                            # bit-exact and the controller can never stall replaying one action.
                            chunk = [[actions[i][0], actions[i][1]]]
                            stats["reference"] += 1
                        else:
                            # replan: aim the short plan at where the reference is a horizon past the phase estimate
                            t_end = tick + a.horizon * hold
                            if a.no_resync:
                                gx, gy = ref_at_tick.get(t_end, (x, y))
                            else:
                                gx, gy = tracker.pos_at_index(max(idx, i) + a.horizon)
                            snap = b.snapshot()
                            mean = np.array([actions[i + k2] if i + k2 < len(actions) else actions[-1] for k2 in range(a.horizon)], dtype=float)
                            std = np.full((a.horizon, 2), a.std); best = None
                            for it in range(a.iters):
                                plans = np.clip(mean[None, :, :] + rng.normal(0, std, size=(a.pop, a.horizon, 2)), -128, 128)
                                plans[0] = mean
                                res = b.rollout_batch(snap, plans.tolist(), hold, {"x0": gx - 2, "x1": gx + 2, "y0": gy - 2, "y1": gy + 2})
                                res = np.array(res)
                                fit = -res[:, 0] - 1000.0 * res[:, 3]
                                order = np.argsort(fit)[::-1]
                                if best is None or fit[order[0]] > best[0]: best = (float(fit[order[0]]), plans[order[0]].copy())
                                elites = plans[order[:a.elite]]
                                mean = 0.4 * mean + 0.6 * elites.mean(0); std = np.maximum(0.4 * std + 0.6 * elites.std(0), 8.0)
                            b.restore(snap)
                            chunk = best[1][:a.commit].tolist()
                            stats["replans"] += 1
                        for ax, ay in chunk:
                            if noise > 0:
                                ax = float(np.clip(ax + rng.normal(0, noise), -128, 128))
                                ay = float(np.clip(ay + rng.normal(0, noise), -128, 128))
                            tr = b.step_commands([{"x": float(ax), "y": float(ay), "id": cid + k} for k in range(hold)])
                            cid += hold
                            if not tr: break
                            i += 1
                            if tr[-1]["dead"] or tr[-1]["success"]:
                                st = tr[-1]; dead = bool(st["dead"]); success = bool(st["success"]); break
                        if dead or success: break
                        if a.max_decisions and i >= a.max_decisions: break
                    fin = b.evaluate("window.research.state()")
                    row = {"seed": seed, "noise": noise, "trial": trial, "decisions": i, "tick": fin["tick"],
                           "x": fin["player_world_x"], "y": fin["player_world_y"], "dead": dead, "success": success,
                           "replans": stats["replans"], "on_reference": stats["reference"], "resyncs": stats["resyncs"],
                           "max_dev": round(stats["max_dev"], 4),
                           "mean_dev": round(stats["dev_sum"] / max(1, stats["dev_n"]), 6),
                           "elapsed_s": round(time.time() - t0, 1)}
                    rows.append(row); print(json.dumps(row), flush=True)
    (out / "eval.json").write_text(json.dumps(rows, indent=1))
    for noise in a.noise:
        rs = [r for r in rows if r["noise"] == noise]
        print(f"noise {noise:5g}: reached summit {sum(1 for r in rs if r['success'])}/{len(rs)}, "
              f"median final y {np.median([r['y'] for r in rs]):.1f}, mean max_dev {np.mean([r['max_dev'] for r in rs]):.4f}")


if __name__ == "__main__":
    main()
