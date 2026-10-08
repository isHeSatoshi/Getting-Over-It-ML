"""Closed-loop policy distillation (behaviour cloning) from the verified open-loop routes.

The search produces open-loop traces: a list of pointer offsets that only works if the run starts
exactly on the reference trajectory. A policy has to act from whatever state it is in. This trains one
by imitation: replay the verified routes in the real game, record (state, action) at every decision
boundary, fit a small MLP, then roll the MLP out closed-loop from ordinary spawn and report how far it
gets. No physics, reward or route is changed; the routes are only read.

  python explore/policy_bc.py collect --routes explore/runs/e28_SUCCESS_s3100.json explore/runs/e26_best_14564.json
  python explore/policy_bc.py train --data explore/runs/policy_bc/data.npz --out explore/runs/policy_bc
  python explore/policy_bc.py eval --model explore/runs/policy_bc/model.pt --seeds 9001 9002 9003 --secs 240

Features are the game's own state variables (velocities, hammer geometry, contact flags, control memory);
actions are the pointer offset in [-128,128]^2 held for `hold` ticks, exactly the search's interface.
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np

HOLD_DEFAULT = 4
# Fixed feature order and scale factors (see `feat`); documented so a saved model stays reproducible.
FEATURES = ["y", "x", "pvx", "pvy", "hdx", "hdy", "hvx", "hvy", "sin_a", "cos_a", "homega",
            "body_hit", "hammer_hit", "air", "last_tx", "last_ty", "effort", "last_effort",
            "off_x", "off_y", "mem_x", "mem_y", "hdist", "svx", "svy"]
SCALE = {"y": 16000.0, "x": 4000.0, "pvx": 20.0, "pvy": 20.0, "hdx": 200.0, "hdy": 200.0, "hvx": 20.0, "hvy": 20.0,
         "sin_a": 1.0, "cos_a": 1.0, "homega": 1.0, "body_hit": 1.0, "hammer_hit": 1.0, "air": 200.0,
         "last_tx": 128.0, "last_ty": 128.0, "effort": 128.0, "last_effort": 128.0, "off_x": 128.0, "off_y": 128.0,
         "mem_x": 128.0, "mem_y": 128.0, "hdist": 200.0, "svx": 20.0, "svy": 20.0}


def feat(s):
    """State dict (research/runtime.js state()) -> fixed-order float vector."""
    p = (s.get("player_world_x", 0.0), s.get("player_world_y", 0.0))
    h = (s.get("hammer_world_x", 0.0), s.get("hammer_world_y", 0.0))
    a = float(s.get("hammer_angle_rad", 0.0))
    raw = {"y": p[1], "x": p[0], "pvx": s.get("player_vx", 0.0), "pvy": s.get("player_vy", 0.0),
           "hdx": h[0] - p[0], "hdy": h[1] - p[1], "hvx": s.get("hammer_vx", 0.0), "hvy": s.get("hammer_vy", 0.0),
           "sin_a": math.sin(a), "cos_a": math.cos(a), "homega": s.get("hammer_angular_velocity", 0.0),
           "body_hit": 1.0 if s.get("body_collision") else 0.0, "hammer_hit": 1.0 if s.get("hammer_collision") else 0.0,
           "air": s.get("hammer_air", 0.0), "last_tx": s.get("last_tx", 0.0), "last_ty": s.get("last_ty", 0.0),
           "effort": s.get("effort", 0.0), "last_effort": s.get("last_effort", 0.0),
           "off_x": s.get("offset_x", 0.0), "off_y": s.get("offset_y", 0.0),
           "mem_x": s.get("control_error_memory_x", 0.0), "mem_y": s.get("control_error_memory_y", 0.0),
           "hdist": s.get("last_hammer_distance", 0.0),
           "svx": s.get("player_impulse_vx", 0.0), "svy": s.get("player_impulse_vy", 0.0)}
    return np.array([raw[k] / SCALE[k] for k in FEATURES], dtype=np.float32)


def collect(a):
    from research.fast_bridge import FastBridge
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    X, Y, meta = [], [], []
    with FastBridge(headless=True) as b:
        for route_path in a.routes:
            route = json.loads(Path(route_path).read_text())
            hold = int(route.get("hold", HOLD_DEFAULT))
            b.reset(a.seed)
            prev = b.evaluate("window.research.state()")
            cid = 1
            n = 0
            for ax, ay in route["actions"]:
                X.append(feat(prev)); Y.append([ax, ay])
                cmds = [{"x": ax, "y": ay, "id": cid + k} for k in range(hold)]
                cid += hold
                tr = b.step_commands(cmds)
                n += 1
                if not tr: break
                prev = tr[-1]
                if prev["dead"] or prev["success"]: break
            meta.append({"route": str(route_path), "hold": hold, "decisions": n})
            print(f"collected {n} decisions from {route_path}", flush=True)
    X = np.asarray(X, dtype=np.float32); Y = np.asarray(Y, dtype=np.float32)
    np.savez_compressed(out / "data.npz", X=X, Y=Y, features=np.array(FEATURES), meta=json.dumps(meta))
    print(json.dumps({"decisions": int(len(X)), "features": len(FEATURES), "routes": meta}, indent=1))


def train(a):
    import torch
    from torch import nn
    d = np.load(a.data, allow_pickle=True)
    X = torch.from_numpy(d["X"]); Y = torch.from_numpy(d["Y"])
    torch.manual_seed(a.seed)
    model = nn.Sequential(nn.Linear(X.shape[1], a.hidden), nn.Tanh(), nn.Linear(a.hidden, a.hidden), nn.Tanh(), nn.Linear(a.hidden, 2))
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    lossf = nn.MSELoss()
    n = len(X)
    for epoch in range(a.epochs):
        perm = torch.randperm(n)
        total = 0.0
        for i in range(0, n, a.batch):
            idx = perm[i:i + a.batch]
            opt.zero_grad()
            pred = model(X[idx]) * 128.0
            loss = lossf(pred, Y[idx])
            loss.backward(); opt.step()
            total += float(loss) * len(idx)
        if (epoch + 1) % max(1, a.epochs // 10) == 0:
            print(f"epoch {epoch + 1:4d} mse {total / n:8.3f}  (units^2)", flush=True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "features": FEATURES, "scale": SCALE, "hidden": a.hidden,
                "data": str(a.data), "epochs": a.epochs, "lr": a.lr, "seed": a.seed}, out / "model.pt")
    print("saved", out / "model.pt")


def load_model(path):
    import torch
    from torch import nn
    blob = torch.load(path, weights_only=False)
    model = nn.Sequential(nn.Linear(len(blob["features"]), blob["hidden"]), nn.Tanh(),
                          nn.Linear(blob["hidden"], blob["hidden"]), nn.Tanh(), nn.Linear(blob["hidden"], 2))
    model.load_state_dict(blob["state_dict"]); model.eval()
    return model, blob


def eval_policy(a):
    import torch
    from research.fast_bridge import FastBridge
    model, blob = load_model(a.model)
    rows = []
    with FastBridge(headless=True) as b:
        for seed in a.seeds:
            b.reset(seed)
            cid = 1; t0 = time.time(); maxy = -1e9; dead = False; success = False; n = 0
            while time.time() - t0 < a.secs:
                st = b.evaluate("window.research.state()")
                with torch.no_grad():
                    act = (model(torch.from_numpy(feat(st)).unsqueeze(0)) * 128.0).clamp(-128, 128).numpy()[0]
                cmds = [{"x": float(act[0]), "y": float(act[1]), "id": cid + k} for k in range(a.hold)]
                cid += a.hold
                tr = b.step_commands(cmds)
                if not tr: break
                s = tr[-1]; n += 1
                maxy = max(maxy, s["player_world_y"])
                dead = bool(s["dead"]); success = bool(s["success"])
                if dead or success: break
            row = {"seed": seed, "decisions": n, "ticks": cid - 1, "max_y": maxy, "final_y": s["player_world_y"],
                   "final_x": s["player_world_x"], "dead": dead, "success": success, "elapsed_s": round(time.time() - t0, 1)}
            rows.append(row); print(json.dumps(row), flush=True)
            if a.trace_out:
                Path(a.trace_out).with_suffix(f".seed{seed}.json").write_text(json.dumps({"seed": seed, "row": row}))
    out = Path(a.out or Path(a.model).parent); out.mkdir(parents=True, exist_ok=True)
    (out / "eval.json").write_text(json.dumps(rows, indent=1))
    print("mean max_y", float(np.mean([r["max_y"] for r in rows])), "best", float(np.max([r["max_y"] for r in rows])))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("--routes", nargs="+", required=True)
    c.add_argument("--out", default="explore/runs/policy_bc"); c.add_argument("--seed", type=int, default=0)
    c.set_defaults(func=collect)
    t = sub.add_parser("train"); t.add_argument("--data", required=True); t.add_argument("--out", required=True)
    t.add_argument("--hidden", type=int, default=256); t.add_argument("--epochs", type=int, default=300)
    t.add_argument("--batch", type=int, default=256); t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--seed", type=int, default=0); t.set_defaults(func=train)
    e = sub.add_parser("eval"); e.add_argument("--model", required=True); e.add_argument("--seeds", type=int, nargs="+", required=True)
    e.add_argument("--secs", type=float, default=240); e.add_argument("--hold", type=int, default=HOLD_DEFAULT)
    e.add_argument("--out", default=None); e.add_argument("--trace-out", default=None); e.set_defaults(func=eval_policy)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
