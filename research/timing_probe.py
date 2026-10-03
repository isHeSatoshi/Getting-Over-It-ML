"""Bounded matched-trajectory timing probe, not training or policy competence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from research.backends import make_bridge
from research.browser_bridge import ROOT
from research.fast_fidelity import compare
from research.milestone_baselines import metrics
from research.milestones import FIRST_LEDGE, Milestone, MilestoneTracker
from research.provenance import fingerprint
from research.trajectory_search import commands_from_knots

# Secondary diagnostic only. The frozen pilot's central-landing benchmark
# remains unchanged; actual body support can occur at the platform's edge.
PLATFORM_SUPPORT = Milestone("first_platform_support_diagnostic_v2",
                            285.0, 345.0, 100.0, 112.0)


def support_metrics(trace):
    tracker = MilestoneTracker((PLATFORM_SUPPORT,))
    tracker.advance(trace)
    return tracker.summary()


def hold_targets(commands, repeat, phase=0):
    if (not isinstance(repeat, int) or isinstance(repeat, bool) or not 1 <= repeat <= 16
            or not isinstance(phase, int) or not 0 <= phase < repeat or not commands):
        raise ValueError("Invalid target-hold timing")
    result = []
    for index in range(len(commands)):
        anchor = max(0, index - (index - phase) % repeat)
        result.append({**commands[anchor], "id": index + 1})
    return result


def replay_targets(commands, repeat, phase=0, motion_ticks=480):
    if not isinstance(motion_ticks, int) or not 1 <= motion_ticks <= len(commands):
        raise ValueError("Invalid motion tick budget")
    motion = hold_targets(commands[:motion_ticks], repeat, phase)
    return motion + [{**motion[-1], "id": index + 1}
                     for index in range(motion_ticks, len(commands))]


def load_trajectory(path, current):
    payload = path.read_bytes()
    report = json.loads(payload)
    for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
        if report["provenance"][key] != current[key]:
            raise ValueError("Trajectory game/assets mismatch: " + key)
    for key in ("research/runtime.js", "research/collision_memo.js"):
        if report["provenance"]["source_sha256"][key] != current["source_sha256"][key]:
            raise ValueError("Trajectory physics contract changed: " + key)
    if report["benchmark"] != FIRST_LEDGE.__dict__:
        raise ValueError("Trajectory benchmark changed")
    search = report["bounded_search"]
    # The original bounded-search report predates recording these constants.
    # Its documented protocol was 480 motion ticks and 120 constant hold ticks.
    if search["ticks_per_candidate_max"] != 600 or search.get("frame_skip", 1) != 1:
        raise ValueError("Expected the documented successful per-tick search protocol")
    if not report["search_reference_replay"]["milestone_success"][FIRST_LEDGE.name]:
        raise ValueError("Source is not a reference-validated ledge trajectory")
    knots = np.asarray(search["best_knots"], dtype=np.float64)
    if knots.shape != (25, 2) or not np.isfinite(knots).all() or np.abs(knots).max() > 128:
        raise ValueError("Invalid original trajectory knots")
    commands = commands_from_knots(knots, 480)
    commands.extend([{**commands[-1], "id": 481 + index} for index in range(120)])
    return commands, hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-report", required=True, type=Path)
    args = parser.parse_args()
    if not args.source_report.is_absolute():
        parser.error("Pass an absolute trusted trajectory report path")
    provenance = fingerprint()
    commands, source_hash = load_trajectory(args.source_report, provenance)
    cases = {"per_tick": commands}
    cases.update({f"four_tick_phase_{phase}": replay_targets(commands, 4, phase)
                  for phase in range(4)})
    output = ROOT / "artifacts" / (
        "timing_probe_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "provenance": provenance, "source_report_sha256": source_hash,
        "benchmark": FIRST_LEDGE.__dict__,
        "protocol": {"ordinary_start": True, "placement": False, "training": False,
                     "motion_ticks": 480, "hold_ticks": 120, "physics_hz": 30,
                     "seed": 42, "max_requested_ticks_all_backends": 6000},
        "cases": {},
        "limit": "Open-loop replay/sampling sensitivity, not proof that four-tick "
                 "feedback is incapable, not a learned policy, and not game completion.",
        "secondary_support_contract": PLATFORM_SUPPORT.__dict__,
    }
    with make_bridge("reference", "selenium") as reference, make_bridge("fast") as fast:
        for name, targets in cases.items():
            a_start = reference.reset(42)
            b_start = fast.reset(42)
            compare([a_start], [b_start])
            a = reference.step_commands(targets)
            b = fast.step_commands(targets)
            errors = compare(a, b)
            measurement = metrics(a_start, a)
            if name == "per_tick" and not measurement["milestone_success"][FIRST_LEDGE.name]:
                raise AssertionError("Known per-tick reference trajectory failed to reproduce")
            report["cases"][name] = {
                **measurement, "requested_ticks": len(targets), "max_fast_reference_error": max(errors.values()),
                "final_x": a[-1]["player_world_x"], "final_y": a[-1]["player_world_y"],
                "secondary_platform_support": support_metrics(a),
            }
            (output / (name + ".json")).write_text(json.dumps({
                "commands": targets[:len(a)], "start": a_start, "reference": a, "fast": b,
            }), encoding="utf-8")
            print(name, json.dumps(report["cases"][name]), flush=True)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
