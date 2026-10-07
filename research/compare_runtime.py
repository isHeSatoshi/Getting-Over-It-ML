"""Bounded fidelity ablations and a forensic trace of the obsolete Node backend."""
import argparse
from datetime import datetime, timezone
import json
import math

from research.browser_bridge import BrowserBridge, ROOT
from research.validate import PHYSICAL
from vm_bridge.node_bridge import NodeBridge


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    args = parser.parse_args()
    commands = [{"x": 90 * math.cos(-i * math.pi / 60),
                 "y": 90 * math.sin(-i * math.pi / 60), "id": i + 1} for i in range(180)]
    output = ROOT / "artifacts" / ("fidelity_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    configurations = {
        "reference": {},
        "interpreted": {"compiled": "false"},
        "packaged_stage": {"width": 640, "height": 480, "fps": 60},
    }
    traces, summaries = {}, {}
    for name, config in configurations.items():
        with BrowserBridge(driver=args.driver, runtime_config=config) as bridge:
            start = bridge.reset(42)
            trace = bridge.step_commands(commands)
            traces[name] = trace
            summaries[name] = {
                "metadata": bridge.evaluate("window.research.metadata()"),
                "start": [start["player_world_x"], start["player_world_y"]],
                "end": [trace[-1]["player_world_x"], trace[-1]["player_world_y"]],
                "max_y": max(s["player_world_y"] for s in trace),
            }
    # Differences across backends are compared numerically, not by JSON bytes.
    for name in ("interpreted", "packaged_stage"):
        errors = {k: max(abs(float(a[k]) - float(b[k])) for a, b in
                         zip(traces["reference"], traces[name])) for k in PHYSICAL}
        summaries[name]["max_errors_against_reference"] = errors
        assert max(errors.values()) < 1e-8, f"{name} changed the tested dynamics: {errors}"
    legacy = NodeBridge()
    try:
        legacy_start = legacy.reset()
        trace = [legacy.step_screen_pointer(c["id"], c["x"], c["y"]) for c in commands]
    finally:
        legacy.close()
    traces["legacy_node"] = trace
    summaries["legacy_node"] = {
        "start_y": legacy_start["player_world_y"],
        "x_range": max(s["player_world_x"] for s in trace) - min(s["player_world_x"] for s in trace),
        "max_y": max(s["player_world_y"] for s in trace),
        "frame_counter_regressions": sum(b["frame_id"] < a["frame_id"] for a, b in zip(trace, trace[1:])),
        "claimed_contact_frames": sum(s["contact_flag"] for s in trace),
        "action_count": len(commands),
    }
    (output / "evidence.json").write_text(
        json.dumps({"summaries": summaries, "commands": commands, "traces": traces}, indent=2), encoding="utf-8")
    print(json.dumps(summaries, indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
