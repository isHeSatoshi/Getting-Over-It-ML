"""Bounded, trace-producing experiments, never training."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import platform
import time

from research.browser_bridge import BrowserBridge, ROOT


def summarize(start, trace):
    states = [start] + trace
    xs = [s["player_world_x"] for s in states]
    ys = [s["player_world_y"] for s in states]
    return {
        "ticks": len(trace), "start_x": xs[0], "start_y": ys[0],
        "end_x": xs[-1], "end_y": ys[-1],
        "x_range": max(xs) - min(xs), "y_range": max(ys) - min(ys),
        "max_gain": max(ys) - ys[0], "retained_gain": ys[-1] - ys[0],
        "body_hit_frames": sum(s["body_collision"] for s in trace),
        "hammer_hit_frames": sum(s["hammer_collision"] for s in trace),
        "dead": states[-1]["dead"], "success": states[-1]["success"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    parser.add_argument("--ticks", type=int, default=240)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.ticks <= 1200:
        parser.error("Diagnostic budget must be 1..1200 ticks per probe")
    output = ROOT / "artifacts" / ("diagnostic_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    experiments = {
        "idle": lambda i: (0, 0),
        "right": lambda i: (90, 0),
        "left": lambda i: (-90, 0),
        "up": lambda i: (0, 80),
        "down": lambda i: (0, -80),
        "circle_cw": lambda i: (90 * math.cos(-i * math.pi / 60), 90 * math.sin(-i * math.pi / 60)),
        "circle_ccw": lambda i: (90 * math.cos(i * math.pi / 60), 90 * math.sin(i * math.pi / 60)),
    }
    report = {"project_sha256": hashlib.sha256(
        (ROOT / "Getting Over It v1/assets/project.json").read_bytes()).hexdigest(),
        "seed": args.seed, "python": platform.python_version(), "experiments": {}}
    with BrowserBridge(driver=args.driver) as bridge:
        print("RESET", json.dumps(bridge.read_state()))
        for name, policy in experiments.items():
            start = bridge.reset(args.seed)
            commands = [{"x": policy(i)[0], "y": policy(i)[1], "id": i + 1}
                        for i in range(args.ticks)]
            begin = time.perf_counter()
            trace = bridge.step_commands(commands)
            summary = summarize(start, trace)
            summary["wall_seconds"] = time.perf_counter() - begin
            report["experiments"][name] = summary
            (output / (name + ".json")).write_text(
                json.dumps({"start": start, "commands": commands[:len(trace)], "trace": trace}), encoding="utf-8")
            print(name, json.dumps(summary))
        if bridge.driver:
            bridge.driver.save_screenshot(str(output / "last.png"))
        else:
            bridge._command(["screenshot", str(output / "last.png")])
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
