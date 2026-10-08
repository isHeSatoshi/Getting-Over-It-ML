"""Policy improvement loop: behaviour cloning + DAgger with a CEM expert (the real game in the page).

The verified routes give a policy that only works exactly on the reference trajectory. This closes the
loop: roll the policy out from ordinary spawn in the real game, find where it stalls, and ask the
in-page exact simulator for a short improving segment from that state (receding-horizon CEM, fitness =
retained height after a held suffix). The segment is the expert demonstration; its (state, action)
pairs are added to the training set and the policy is retrained. Repeat.

Nothing here changes physics, rewards or the verified routes; the routes are only read.

  python explore/policy_dagger.py --data explore/runs/policy_bc/data.npz --out explore/runs/policy_dagger \
      --iters 6 --rollout-decisions 3000 --experts 2
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np
from research.fast_bridge import FastBridge
from explore import policy_bc as BC
from explore.mpc_climb import knots_to_actions

HOLD = 4
GOAL = {"x0": 0.0, "x1": 0.0, "y0": 0.0, "y1": 0.0}       # unused; fitness is retained height


def train_model(X, Y, hidden, epochs, seed, warm=None):
    import torch
    from torch import nn
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(X.shape[1], hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 2))
    if warm is not None:
        model.load_state_dict(warm)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    lossf = nn.MSELoss()
    Xt = torch.from_numpy(np.asarray(X, dtype=np.float32)); Yt = torch.from_numpy(np.asarray(Y, dtype=np.float32))
    n = len(Xt)
    for epoch in range(epochs):
        perm = torch.randperm(n)
        for i in range(0, n, 256):
            idx = perm[i:i + 256]
            opt.zero_grad()
            loss = lossf(model(Xt[idx]) * 128.0, Yt[idx])
            loss.backward(); opt.step()
    return model


def act(model, state):
    import torch
    with torch.no_grad():
        a = (model(torch.from_numpy(BC.feat(state)).unsqueeze(0)) * 128.0).clamp(-128, 128).numpy()[0]
    return float(a[0]), float(a[1])


def rollout(b, model, max_decisions, record=True):
    """Closed-loop rollout from ordinary spawn. Returns (trace, actions, states)."""
    b.reset(0)
    states, actions, ys = [], [], []
    prev = b.evaluate("window.research.state()")
    cid = 1
    for _ in range(max_decisions):
        ax, ay = act(model, prev)
        if record:
            states.append(prev); actions.append([ax, ay]); ys.append(prev["player_world_y"])
        tr = b.step_commands([{"x": ax, "y": ay, "id": cid + k} for k in range(HOLD)])
        cid += HOLD
        if not tr: break
        prev = tr[-1]
        if prev["dead"] or prev["success"]: break
    return {"states": states, "actions": actions, "ys": ys, "last": prev, "decisions": len(actions)}


def snapshot_at(b, actions, cx, cy):
    """Deterministic prefix replay: fresh reset, apply `actions`, return an exact snapshot handle."""
    b.reset(0)
    cid = 1
    for ax, ay in actions:
        b.step_commands([{"x": ax, "y": ay, "id": cid + k} for k in range(HOLD)])
        cid += HOLD
    b.seed_cell(cx, cy)
    return b.snapshot()


def cem_expert(b, snap, x, y, rng, pop, iters, elite, horizon, knot_every, suffix, std0=60.0):
    """Receding-horizon CEM from `snap`; returns the best plan (list of [x, y] decisions)."""
    K = horizon // knot_every + 1
    mean = np.zeros((K, 2)); std = np.full((K, 2), std0)
    best = None
    for it in range(iters):
        knots = np.clip(rng.normal(mean, std, size=(pop, K, 2)), -128, 128)
        if it == 0: knots[0] = mean
        plans = [np.concatenate([a, np.repeat(a[-1:], suffix, 0)]) for a in (knots_to_actions(k, horizon) for k in knots)]
        res = []
        for i in range(0, pop, 64):
            res += b.rollout_batch(snap, [p.tolist() for p in plans[i:i + 64]], HOLD, GOAL)
        res = np.array(res)
        fit = res[:, 2] - 1000.0 * res[:, 3]           # retained height after the held suffix
        order = np.argsort(fit)[::-1]
        if best is None or fit[order[0]] > best[0]:
            best = (float(fit[order[0]]), plans[order[0]][:horizon].copy(), float(res[order[0], 2]))
        elites = knots[order[:elite]]
        mean = 0.4 * mean + 0.6 * elites.mean(0); std = np.maximum(0.4 * std + 0.6 * elites.std(0), 10.0)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="explore/runs/policy_bc/data.npz")
    ap.add_argument("--out", default="explore/runs/policy_dagger")
    ap.add_argument("--iters", type=int, default=6)
    ap.add_argument("--rollout-decisions", type=int, default=3000)
    ap.add_argument("--experts", type=int, default=2, help="stall states corrected per iteration")
    ap.add_argument("--expert-seg", type=int, default=40, help="decisions of expert segment to keep per state")
    ap.add_argument("--horizon", type=int, default=24); ap.add_argument("--knot-every", type=int, default=4)
    ap.add_argument("--suffix", type=int, default=23); ap.add_argument("--commit", type=int, default=8)
    ap.add_argument("--pop", type=int, default=48); ap.add_argument("--cem-iters", type=int, default=3)
    ap.add_argument("--elite", type=int, default=8)
    ap.add_argument("--hidden", type=int, default=256); ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--cx", type=float, default=16); ap.add_argument("--cy", type=float, default=8)
    ap.add_argument("--min-gain", type=float, default=20.0, help="expert segment must raise retained Y by this much to be kept")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    log = (out / "log.jsonl").open("w")
    d = np.load(a.data, allow_pickle=True)
    X = [d["X"]]; Y = [d["Y"]]
    model = None
    with FastBridge(headless=True) as b:
        for it in range(a.iters + 1):
            t0 = time.time()
            model = train_model(np.concatenate(X), np.concatenate(Y), a.hidden, a.epochs, a.seed + it, warm=model.state_dict() if model else None)
            roll = rollout(b, model, a.rollout_decisions)
            ys = roll["ys"]; best_i = int(np.argmax(ys)) if ys else 0
            rec = {"iter": it, "decisions": roll["decisions"], "max_y": float(np.max(ys)) if ys else None,
                   "final_y": roll["last"]["player_world_y"], "dead": bool(roll["last"]["dead"]),
                   "success": bool(roll["last"]["success"]), "best_decisions": best_i, "t": round(time.time() - t0, 1),
                   "train_rows": int(len(np.concatenate(X)))}
            print(json.dumps(rec), flush=True)
            if it == a.iters or roll["last"]["success"]:
                log.write(json.dumps(rec) + "\n"); break
            # expert corrections at the best state and at the last few states before death
            picks = [best_i]
            if roll["decisions"] > 10:
                picks += [max(0, roll["decisions"] - 1 - k * 25) for k in range(a.experts - 1)]
            newX, newY, gains = [], [], []
            for i, pi in enumerate(picks):
                if pi >= len(roll["actions"]): continue
                x_i = roll["states"][pi]["player_world_x"]; y_i = roll["states"][pi]["player_world_y"]
                snap = snapshot_at(b, roll["actions"][:pi], a.cx, a.cy)
                gain, plan, end_y = cem_expert(b, snap, x_i, y_i, rng, a.pop, a.cem_iters, a.elite, a.horizon, a.knot_every, a.suffix)
                if gain < y_i + a.min_gain:
                    b.drop_snapshot(snap); continue
                # follow the plan, committing `commit` decisions at a time, recording (state, action)
                seg = plan[:a.expert_seg]
                cur = snap; got = 0
                while got < len(seg):
                    chunk = seg[got:got + a.commit]
                    st = b.restore(cur)
                    for ax, ay in chunk:
                        newX.append(BC.feat(st)); newY.append([ax, ay])
                        st = b.step_commands([{"x": float(ax), "y": float(ay), "id": 1}])[-1]
                    got += len(chunk)
                b.drop_snapshot(cur)
                gains.append({"pick": pi, "x": round(x_i, 1), "y": round(y_i, 1), "expert_end_y": round(end_y, 1),
                              "gain": round(gain - y_i, 1), "pairs": len(newX)})
            if newX:
                X.append(np.asarray(newX, dtype=np.float32)); Y.append(np.asarray(newY, dtype=np.float32))
            rec["experts"] = gains
            log.write(json.dumps(rec) + "\n"); log.flush()
            print("  experts:", json.dumps(gains), flush=True)
    import torch
    torch.save({"state_dict": model.state_dict(), "features": BC.FEATURES, "scale": BC.SCALE, "hidden": a.hidden,
                "data": a.data, "iters": a.iters, "seed": a.seed}, out / "model.pt")
    print("saved", out / "model.pt")


if __name__ == "__main__":
    main()
