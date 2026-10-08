"""Baselines and one-factor-at-a-time ablations for the Go-Explore climb (equal budget, fixed seeds).

Every config is a Go-Explore run (or the random-restart baseline) with `--workers` islands started in
parallel for `--secs`, exactly like `explore/run_islands.py`. Configs that start from an earlier
verified route publish it into a fresh share dir first, so every island imports it at its first sync.
Results append to `results.jsonl` (one line per config-seed) and `--table` renders the markdown table.

  python explore/experiments.py list
  python explore/experiments.py run --suite last_leg --seeds 5100 5200 5300 --secs 180
  python explore/experiments.py table

Metrics per config-seed: best retained progress over the round, whether any island reached the win
flag (Y > 16000), seconds to first success, imports, hold tests. Budgets are wall-clock seconds of
search; every config in a suite gets the same one.
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "explore" / "runs"
RESULTS = RUNS / "experiments" / "results.jsonl"

# Full configs reproduced from the E-series runs (see explore/LOG.md). `args` are goexplore.py flags,
# `env` are process environment additions (PHI_TAG/PHI_MAXX select the offline potential).
FULL_MID = ["--phi", "--front-scale", "30", "--gait-frac", "0.4", "--local-radius", "250",
            "--sync-s", "60", "--import-margin", "250", "--stall-s", "560", "--max-cells", "9000",
            "--heap-mb", "450", "--min-len", "6", "--max-len", "48"]
FULL_LAST = ["--front-scale", "60", "--gait-frac", "0.3", "--local-radius", "0",
             "--sync-s", "60", "--import-margin", "100", "--stall-s", "380", "--max-cells", "9000",
             "--heap-mb", "450", "--min-len", "6", "--max-len", "48"]
# Potentials saved by explore/potential.py. Tags map to files: "" -> phi.npy (PHI_COVER=1, full goal),
# "_full2" -> phi_full2.npy (PHI_COVER=6, full goal; the potential E24-E28 used), "_ramp" -> phi_ramp.npy
# (PHI_GOAL_BOX=2900,3600,10400,10700, the E20-E23 staged goal), "_blob" -> phi_blob.npy (E21 goal).
ENV_FULL = {"PHI_TAG": "_full2", "PHI_MAXX": "4600"}


def flag(args, name, value):
    """Copy of `args` with `name`'s value replaced by `value` (appended when absent)."""
    out = list(args)
    if name in out:
        out[out.index(name) + 1] = value
    else:
        out += [name, value]
    return out

SUITES = {
    # From ordinary spawn: how far does each method get with the same budget?
    "baselines": [
        {"name": "goexplore_height", "kind": "goexplore", "start": None, "args": []},
        {"name": "random_restart", "kind": "random_restart", "start": None, "args": []},
    ],
    # Last leg: from the verified Y 14884 route, the config that reached the summit (E28).
    "last_leg": [
        {"name": "full", "kind": "goexplore", "start": "e28_share/best_3000.json", "args": FULL_LAST},
        {"name": "no_hold_test", "kind": "goexplore", "start": "e28_share/best_3000.json", "args": FULL_LAST + ["--no-hold-test"]},
        {"name": "no_gait", "kind": "goexplore", "start": "e28_share/best_3000.json",
         "args": flag(FULL_LAST, "--gait-frac", "0")},
        {"name": "with_potential", "kind": "goexplore", "start": "e28_share/best_3000.json", "args": FULL_LAST + ["--phi"],
         "env": ENV_FULL},
    ],
    # Mid leg: from the verified Y 10808 route, the config that reached Y 14564 (E26).
    "mid_leg": [
        {"name": "full", "kind": "goexplore", "start": "e25_best_10808.json", "args": FULL_MID, "env": ENV_FULL},
        {"name": "no_potential", "kind": "goexplore", "start": "e25_best_10808.json",
         "args": [x for x in FULL_MID if x != "--phi"], "env": {}},
        {"name": "no_ceiling_penalty", "kind": "goexplore", "start": "e25_best_10808.json", "args": FULL_MID,
         "env": {"PHI_TAG": "", "PHI_MAXX": "4600"}},
        {"name": "no_gait", "kind": "goexplore", "start": "e25_best_10808.json",
         "args": flag(FULL_MID, "--gait-frac", "0"), "env": ENV_FULL},
    ],
    # Staged goals: from the verified Y 9341 route, the final goal vs the first staged goal (the
    # plateau above the west ramp, PHI_GOAL_BOX=2900,3600,10400,10700 -> phi_ramp.npy).
    "staged_goals": [
        {"name": "final_goal", "kind": "goexplore", "start": "e14_best_9341.json", "args": FULL_MID,
         "env": ENV_FULL},
        {"name": "stage1_ramp_goal", "kind": "goexplore", "start": "e14_best_9341.json", "args": FULL_MID,
         "env": {"PHI_TAG": "_ramp", "PHI_MAXX": "4600"}},
    ],
}


def route_end(route_path):
    """Replay a saved route headless and return its final (x, y). Cached; also used to re-rank a start
    route under a different potential, so the published progress is in the units the islands compare."""
    cache_path = RUNS / "experiments" / "route_ends.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    key = str(Path(route_path).relative_to(ROOT)) if str(route_path).startswith(str(ROOT)) else str(route_path)
    if key not in cache:
        from research.fast_bridge import FastBridge
        route = json.loads(Path(route_path).read_text())
        hold = int(route.get("hold", 4)); cid = 1; cmds = []
        for ax, ay in route["actions"]:
            for _ in range(hold):
                cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
        with FastBridge(headless=True) as b:
            b.reset(0)
            last = None
            for i in range(0, len(cmds), 2400):
                tr = b.step_commands(cmds[i:i + 2400])
                if tr: last = tr[-1]
                if last and (last["dead"] or last["success"]): break
        cache[key] = [last["player_world_x"], last["player_world_y"]]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=1))
    return cache[key]


def progress_of(cfg, x, y):
    """Progress scalar the islands will compute for a route end state: height, or -phi under --phi."""
    if "--phi" not in cfg["args"]:
        return float(y)
    import numpy as np
    tag = cfg.get("env", {}).get("PHI_TAG", "")
    phi = np.load(ROOT / "explore" / "world" / f"phi{tag}.npy")
    meta = json.loads((ROOT / "explore" / "world" / "world_meta.json").read_text())
    r = min(phi.shape[0] - 1, max(0, int(round((meta["y1"] - y) / meta["unit"]))))
    c = min(phi.shape[1] - 1, max(0, int(round((x - meta["x0"]) / meta["unit"]))))
    return -float(phi[r, c])


def publish_start(cfg, share):
    """Publish the config's start route into the share dir as a foreign best (islands import it)."""
    if not cfg.get("start"):
        return None
    src = RUNS / cfg["start"]
    d = json.loads(src.read_text())
    x, y = (d["x"], d["y"]) if d.get("y", 0) >= 0 else route_end(src)
    (Path(share) / "best_3000.json").write_text(json.dumps(
        {"seed": 3000, "y": progress_of(cfg, x, y), "x": x, "hold": d.get("hold", 4), "actions": d["actions"]}))
    return str(src)


def run_seed(cfg, seed, secs, workers, out_root):
    # Include the suite in the path: suites share config names (e.g. "full"), and without it a later
    # run overwrites the earlier one's artifacts (the recorded rows stay correct, the files do not).
    run_dir = Path(out_root) / f"{cfg['suite']}_{cfg['name']}_s{seed}"
    share = run_dir / "share"
    share.mkdir(parents=True, exist_ok=True)
    started = publish_start(cfg, share)
    env = dict(os.environ, PYTHONPATH=str(ROOT), **cfg.get("env", {}))
    procs = []
    for i in range(workers):
        wseed = seed + i
        out = run_dir / f"w{i}"
        out.mkdir(parents=True, exist_ok=True)
        if cfg["kind"] == "goexplore":
            cmd = [sys.executable, str(ROOT / "explore" / "goexplore.py"), "--secs", str(secs), "--seed", str(wseed),
                   "--share-dir", str(share), "--out", str(out), "--cx", "16", "--cy", "8"] + cfg["args"]
        else:
            cmd = [sys.executable, str(ROOT / "explore" / "random_restart.py"), "--secs", str(secs), "--seed", str(wseed),
                   "--out", str(out), "--cx", "16", "--cy", "8"] + cfg["args"]
        procs.append(subprocess.Popen(cmd, stdout=(out / "log.txt").open("w"), stderr=subprocess.STDOUT, cwd=ROOT, env=env))
    t0 = time.time()
    for p in procs: p.wait()
    summaries = []
    for i in range(workers):
        out = run_dir / f"w{i}"
        s = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {"success": False, "maxRetainedY": None}
        s["success_path"] = (out / "SUCCESS_path.json").exists()
        s["worker"] = i
        summaries.append(s)
    row = {"suite": cfg["suite"], "config": cfg["name"], "seed": seed, "secs": secs, "workers": workers,
           "kind": cfg["kind"], "start": started, "elapsed_s": round(time.time() - t0, 1),
           "args": cfg["args"], "env": cfg.get("env", {}), "units": "phi" if "--phi" in cfg["args"] else "height",
           "best_retained_progress": max([s["maxRetainedY"] for s in summaries if s.get("maxRetainedY") is not None], default=None),
           "best_retained_y": max([s.get("best_xy", [0, 0])[1] for s in summaries
                                   if s.get("maxRetainedY") is not None], default=None) if "--phi" not in cfg["args"] else None,
           "maxY_any": max([s.get("maxY_any", -1e9) for s in summaries], default=None),
           "success": any(s["success"] for s in summaries),
           "success_workers": sum(1 for s in summaries if s["success"]),
           "success_paths": sum(1 for s in summaries if s["success_path"]),
           "ticks": sum(s.get("ticks", 0) for s in summaries),
           "hold_tests": sum(s.get("hold_tests", 0) for s in summaries),
           "workers_detail": [{"success": s["success"], "maxRetainedY": s.get("maxRetainedY"),
                               "maxY_any": s.get("maxY_any"), "ticks": s.get("ticks"), "ticks_per_s": s.get("ticks_per_s")}
                              for s in summaries]}
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def table(path=RESULTS):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines()] if Path(path).exists() else []
    if not rows:
        print("no results yet"); return
    by = {}
    for r in rows:
        by.setdefault((r["suite"], r["config"]), []).append(r)
    order = [c["name"] for s in SUITES.values() for c in s]
    print("| suite | config | seeds | budget/run | best retained progress (max over seeds) | units | success runs | mean ticks/s |")
    print("|---|---|---|---|---|---|---|---|")
    for (suite, cfg), rs in sorted(by.items(), key=lambda kv: (list(SUITES).index(kv[0][0]), order.index(kv[0][1]))):
        prog = [r["best_retained_progress"] for r in rs if r["best_retained_progress"] is not None]
        tps = [r["ticks"] / max(r["elapsed_s"], 1e-9) for r in rs]
        succ = sum(1 for r in rs if r["success"])
        print(f"| {suite} | {cfg} | {len(rs)} | {rs[0]['secs']:.0f}s x {rs[0]['workers']} islands | "
              f"{max(prog):.1f} | {rs[0].get('units', '?')} | {succ}/{len(rs)} | {sum(tps)/len(tps):.0f} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["list", "run", "table"])
    ap.add_argument("--suite", default=None); ap.add_argument("--config", default=None)
    ap.add_argument("--only", nargs="+", default=None, help="run only these config names (e.g. --only full no_gait)")
    ap.add_argument("--seeds", type=int, nargs="+", default=[5100, 5200, 5300])
    ap.add_argument("--secs", type=float, default=None, help="budget per run (default: suite-specific)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out-root", default=str(RUNS / "experiments"))
    a = ap.parse_args()
    if a.command == "list":
        for suite, cfgs in SUITES.items():
            for c in cfgs:
                print(f"{suite:12s} {c['name']:18s} start={c.get('start')} args={' '.join(c['args'])} env={c.get('env', {})}")
        return
    if a.command == "table":
        table(); return
    suites = [a.suite] if a.suite else list(SUITES)
    default_secs = {"baselines": 300, "last_leg": 180, "mid_leg": 400, "staged_goals": 300}
    for suite in suites:
        for cfg in SUITES[suite]:
            if a.config and cfg["name"] != a.config: continue
            if a.only and cfg["name"] not in a.only: continue
            cfg = dict(cfg, suite=suite)
            secs = a.secs or default_secs[suite]
            for seed in a.seeds:
                print(f"== {suite}/{cfg['name']} seed={seed} secs={secs:.0f}", flush=True)
                row = run_seed(cfg, seed, secs, a.workers, a.out_root)
                print(json.dumps({k: v for k, v in row.items() if k != "workers_detail"}), flush=True)


if __name__ == "__main__":
    main()
