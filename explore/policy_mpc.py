"""Closed-loop policy: receding-horizon CEM on the real game (MPC), optional geometry potential.

A policy has to act from whatever state it is in, not only on the reference trajectory. This one
re-plans from the actual state every `--commit` decisions using the real game as its simulator
(`rollout_batch`), scoring each candidate after a held-pointer suffix so the score is *retained*
progress, never transient flung height. With `--phi` the score is the offline geometry potential
(cost-to-goal) instead of height, with the same dead-end gating the search uses.

Everything is closed loop: the plan is recomputed from the state the game is actually in, so a
perturbation is corrected rather than followed. The committed decisions are a legal action trace, and
the final trace is re-verified with a fresh reset + straight replay (`explore/replay_route.py`).

  python explore/policy_mpc.py --secs 600 --seed 0 --phi --out explore/runs/p_mpc_phi
  python explore/policy_mpc.py --secs 600 --seed 0 --out explore/runs/p_mpc_height
"""
import argparse, json, math, os, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge
from explore.mpc_climb import knots_to_actions

HOLD = 4
GOAL = {"x0": 0.0, "x1": 0.0, "y0": 0.0, "y1": 0.0}          # unused: fitness is retained progress


class Potential:
    """Offline geometry potential (explore/potential.py output) as a scalar progress field."""

    def __init__(self, tag=""):
        self.phi = np.load(f"explore/world/phi_x4{tag}.npy")
        meta = json.load(open("explore/world/world_meta.json"))
        self.unit = meta["unit"] * 4; self.x0 = meta["x0"]; self.y1 = meta["y1"]
        self.maxx = float(os.environ.get("PHI_MAXX", "1e9")); self.miny = float(os.environ.get("PHI_MINY", "-1e9"))

    def __call__(self, x, y):
        r = min(self.phi.shape[0] - 1, max(0, int(round((self.y1 - y) / self.unit))))
        c = min(self.phi.shape[1] - 1, max(0, int(round((x - self.x0) / self.unit))))
        v = -float(self.phi[r, c])
        return v - (1e5 if (y < self.miny or x > self.maxx) else 0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--secs", type=float, default=600)
    ap.add_argument("--phi", action="store_true", help="score with the geometry potential instead of height")
    ap.add_argument("--phi-tag", default="", help="potential file suffix (explore/world/phi_x4<TAG>.npy)")
    ap.add_argument("--horizon", type=int, default=16); ap.add_argument("--knot-every", type=int, default=4)
    ap.add_argument("--suffix", type=int, default=15, help="held-pointer decisions appended (retained test)")
    ap.add_argument("--pop", type=int, default=32); ap.add_argument("--iters", type=int, default=2)
    ap.add_argument("--elite", type=int, default=6); ap.add_argument("--commit", type=int, default=4)
    ap.add_argument("--std", type=float, default=70.0); ap.add_argument("--warm", action=argparse.BooleanOptionalAction, default=True,
                                                                       help="warm-start the CEM mean from the previous plan")
    ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    ap.add_argument("--trace-out", default=None)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    prog = Potential(a.phi_tag) if a.phi else (lambda x, y: y)
    K = a.horizon // a.knot_every + 1
    log = (out / "log.jsonl").open("w")
    with FastBridge(headless=True) as b:
        b.reset(0)
        mean = np.zeros((K, 2)); actions = []; t0 = time.time(); last_log = t0
        state = b.evaluate("window.research.state()")
        maxy = state["player_world_y"]; best = {"x": state["player_world_x"], "y": state["player_world_y"], "p": prog(state["player_world_x"], state["player_world_y"])}
        dead = success = False
        while time.time() - t0 < a.secs and not dead and not success:
            snap = b.snapshot()
            if not a.warm: mean = np.zeros((K, 2))
            for it in range(a.iters):
                knots = np.clip(rng.normal(mean, np.full((K, 2), a.std), size=(a.pop, K, 2)), -128, 128)
                if it == 0: knots[0] = mean
                plans = [np.concatenate([p, np.repeat(p[-1:], a.suffix, 0)]) for p in (knots_to_actions(k, a.horizon) for k in knots)]
                res = []
                for i in range(0, a.pop, 64):
                    res += b.rollout_batch(snap, [p.tolist() for p in plans[i:i + 64]], HOLD, GOAL)
                res = np.array(res)
                fit = np.array([prog(r[1], r[2]) for r in res]) - 1e5 * res[:, 3]
                order = np.argsort(fit)[::-1]
                elites = knots[order[:a.elite]]
                mean = 0.4 * mean + 0.6 * elites.mean(0); std = np.maximum(0.4 * a.std + 0.6 * elites.std(0), 10.0)
            top = order[0]; plan = plans[top][:a.horizon]
            b.restore(snap)
            chunk = plan[:a.commit]
            for ax, ay in chunk:
                tr = b.step_commands([{"x": float(ax), "y": float(ay), "id": 1}])
                if not tr: break
                state = tr[-1]; actions.append([float(ax), float(ay)])
                maxy = max(maxy, state["player_world_y"])
                if prog(state["player_world_x"], state["player_world_y"]) > best["p"]:
                    best = {"x": state["player_world_x"], "y": state["player_world_y"], "p": prog(state["player_world_x"], state["player_world_y"])}
            dead = bool(state["dead"]); success = bool(state["success"])
            # Warm start: shift the knot mean by what was committed, keeping the shape (commit can
            # exceed the knot count, so clamp; the tail knot is repeated).
            shift = min(a.commit, K - 1)
            mean = np.concatenate([mean[shift:], np.repeat(mean[-1:], shift, 0)])
            b.drop_snapshot(snap)
            if time.time() - last_log > 20:
                last_log = time.time()
                print(f"[{last_log - t0:6.0f}s] decisions={len(actions)} x={state['player_world_x']:.0f} y={state['player_world_y']:.0f} "
                      f"maxY={maxy:.0f} bestProg={best['p']:.1f} pred={res[top, 2]:.0f} dead={dead}", flush=True)
        el = time.time() - t0
        trace = {"hold": HOLD, "actions": actions}
        (out / "trace.json").write_text(json.dumps(trace))
        summary = {"args": vars(a), "elapsed_s": round(el, 1), "decisions": len(actions), "ticks": len(actions) * HOLD,
                   "ticks_per_s": round(len(actions) * HOLD / el), "max_y": maxy, "final_x": state["player_world_x"],
                   "final_y": state["player_world_y"], "dead": dead, "success": success,
                   "best_progress": best["p"], "best_xy": [best["x"], best["y"]], "units": "phi" if a.phi else "height"}
        (out / "summary.json").write_text(json.dumps(summary, indent=1))
        print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
