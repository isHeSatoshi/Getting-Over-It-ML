"""Supervisor: run Go-Explore islands in bounded rounds with fresh browsers (bounded memory).

State between rounds lives in --share-dir (each island's best retained path). Each round's
islands import the global best at startup. Stops on success, a global stall, or the round cap.

  python explore/run_islands.py --share-dir explore/runs/e8_share --rounds 6 --round-secs 420
"""
import argparse, glob, json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def global_best(share):
    best = (-1e9, None)
    for f in glob.glob(str(Path(share) / "best_*.json")):
        try:
            d = json.loads(Path(f).read_text())
        except Exception:
            continue
        if d["y"] > best[0]: best = (d["y"], d["seed"])
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--share-dir", required=True); ap.add_argument("--out-root", default=None)
    ap.add_argument("--rounds", type=int, default=6); ap.add_argument("--round-secs", type=float, default=420)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--base-seed", type=int, default=100)
    ap.add_argument("--max-cells", type=int, default=9000); ap.add_argument("--heap-mb", type=float, default=450)
    ap.add_argument("--stall-rounds", type=int, default=3, help="stop after this many rounds without >= min-gain")
    ap.add_argument("--min-gain", type=float, default=25.0)
    ap.add_argument("--extra", default="", help="extra goexplore.py arguments, e.g. '--phi'")
    a = ap.parse_args()
    share = Path(a.share_dir); share.mkdir(parents=True, exist_ok=True)
    out_root = Path(a.out_root or share.parent / (share.name + "_rounds")); out_root.mkdir(parents=True, exist_ok=True)
    log = (out_root / "progress.jsonl").open("a")
    history = [global_best(share)[0]]
    for r in range(a.rounds):
        t0 = time.time(); procs = []
        for i in range(a.workers):
            seed = a.base_seed + r * 10 + i
            out = out_root / f"r{r}_s{seed}"; out.mkdir(parents=True, exist_ok=True)
            cmd = [sys.executable, str(ROOT / "explore" / "goexplore.py"), "--secs", str(a.round_secs), "--seed", str(seed),
                   "--share-dir", str(share), "--out", str(out), "--max-cells", str(a.max_cells), "--heap-mb", str(a.heap_mb)] + a.extra.split()
            procs.append((seed, out, subprocess.Popen(cmd, stdout=(out / "log.txt").open("w"), stderr=subprocess.STDOUT, cwd=ROOT)))
        for _, _, p in procs: p.wait()
        y, who = global_best(share)
        success = [str(o / "SUCCESS_path.json") for _, o, _ in procs if (o / "SUCCESS_path.json").exists()]
        rec = {"round": r, "elapsed_s": round(time.time() - t0), "global_best_retained_y": y, "from_seed": who,
               "exit_codes": [p.returncode for _, _, p in procs], "success_paths": success}
        log.write(json.dumps(rec) + "\n"); log.flush(); print(json.dumps(rec), flush=True)
        history.append(y)
        if success:
            print("SUCCESS", success); return
        if len(history) > a.stall_rounds and history[-1] - history[-1 - a.stall_rounds] < a.min_gain:
            print(f"STALL: gain {history[-1] - history[-1 - a.stall_rounds]:.1f} over {a.stall_rounds} rounds; stopping"); return


if __name__ == "__main__":
    main()
