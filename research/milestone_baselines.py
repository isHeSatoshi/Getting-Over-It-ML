"""Bounded first-ledge baselines and labelled detector calibration, no RL."""
import argparse
from datetime import datetime, timezone
import json
import math
import numpy as np

from research.backends import make_bridge
from research.browser_bridge import ROOT
from research.fast_fidelity import placement_expression
from research.milestones import FIRST_LEDGE, MilestoneTracker
from research.terrain import TerrainMap
from research.diagnose import summarize
from research.trajectory_search import commands_from_knots
from research.provenance import fingerprint


def metrics(start, trace):
    tracker = MilestoneTracker()
    tracker.advance(trace)
    return {**summarize(start, trace), **tracker.summary()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", action="store_true", help="24-candidate bounded exact-game feasibility probe")
    parser.add_argument("--frame-skip", type=int, choices=[1, 4], default=4,
                        help="Search actions use the same held-target timing as the RL interface")
    parser.add_argument("--warm-start-search", type=str, help="Absolute path to a prior trusted baseline report")
    args = parser.parse_args()
    output = ROOT / "artifacts" / ("milestone_baselines_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    report = {"provenance": fingerprint(), "benchmark": FIRST_LEDGE.__dict__, "baselines": {}}
    terrain = TerrainMap()
    report["terrain_surface_samples"] = {str(x): max(y for y in range(251) if terrain.check_collision(x, y))
                                         for x in (305, 315, 325, 335)}
    with make_bridge("reference", "selenium") as bridge:
        bridge.reset(42)
        bridge.evaluate(placement_expression(320, 150))
        calibration = bridge.step_commands([{"x": 0, "y": 0, "id": i + 1} for i in range(180)])
        tracker = MilestoneTracker()
        tracker.advance(calibration)
        report["diagnostic_calibration"] = {"NOT_POLICY_SUCCESS": True, **tracker.summary(),
                                          "settled_y": calibration[-1]["player_world_y"]}
        assert tracker.summary()["milestone_success"][FIRST_LEDGE.name]
        assert calibration[-1]["body_collision"]
        (output / "diagnostic_calibration.json").write_text(json.dumps(calibration), encoding="utf-8")
        rng = np.random.default_rng(0)
        cases = {
            "idle": [{"x": 0, "y": 0, "id": i + 1} for i in range(600)],
            "down_hold": [{"x": 0, "y": -80, "id": i + 1} for i in range(600)],
            "clockwise": [{"x": 90 * math.cos(-i * math.pi / 60), "y": 90 * math.sin(-i * math.pi / 60),
                           "id": i + 1} for i in range(600)],
            "random": [{"x": float(a[0]), "y": float(a[1]), "id": 4 * i + j + 1}
                       for i, a in enumerate(rng.uniform(-128, 128, (150, 2))) for j in range(4)],
        }
        for name, commands in cases.items():
            start = bridge.reset(42)
            trace = bridge.step_commands(commands)
            report["baselines"][name] = metrics(start, trace)
            (output / (name + ".json")).write_text(json.dumps({"start": start, "commands": commands[:len(trace)],
                                                              "trace": trace}), encoding="utf-8")
            print(name, report["baselines"][name], flush=True)
    if args.search:
        rng = np.random.default_rng(0)
        ticks, knots_count = 480, 25
        angle = -np.linspace(0, (ticks - 1) * math.pi / 60, knots_count)
        mean = np.stack((90 * np.cos(angle), 90 * np.sin(angle)), axis=1)
        std = np.full_like(mean, 40.0)
        if args.warm_start_search:
            from pathlib import Path
            warm = Path(args.warm_start_search)
            if not warm.is_absolute():
                parser.error("Warm-start search path must be absolute")
            previous = json.loads(warm.read_text(encoding="utf-8"))
            candidate = np.asarray(previous["bounded_search"]["best_knots"], dtype=float)
            if candidate.shape != mean.shape or not np.isfinite(candidate).all():
                raise ValueError("Incompatible warm-start trajectory")
            mean = candidate
        best_score, best_knots = -math.inf, mean.copy()
        history = []
        def search_commands(knots):
            commands = commands_from_knots(knots, ticks)
            if args.frame_skip == 4:
                commands = [{**commands[i - i % 4], "id": i + 1} for i in range(ticks)]
            return commands
        with make_bridge("fast") as bridge:
            for iteration in range(3):
                candidates = np.clip(rng.normal(mean, std, size=(8, knots_count, 2)), -128, 128)
                candidates[0] = best_knots
                scores = []
                for index, knots in enumerate(candidates):
                    start = bridge.reset(42)
                    commands = search_commands(knots)
                    trace = bridge.step_commands(commands)
                    if trace and not trace[-1]["dead"]:
                        trace += bridge.step_commands([{**commands[-1], "id": ticks + i + 1} for i in range(120)])
                    measure = metrics(start, trace)
                    # Search heuristic only. Success is exclusively the physical
                    # hold predicate, never this distance/coverage score.
                    distances = [math.hypot(s["player_world_x"] - 320, s["player_world_y"] - 104) for s in trace]
                    score = (-min(distances) + 100 * measure["milestone_best_hold_seconds"][FIRST_LEDGE.name]
                             + 1000 * measure["milestone_success"][FIRST_LEDGE.name] - 100 * measure["dead"])
                    scores.append(score)
                    history.append({"iteration": iteration, "candidate": index, "score": score, "metrics": measure})
                    if score > best_score:
                        best_score, best_knots = score, knots.copy()
                    print("search", iteration, index, "score", round(score, 2),
                          "hold", measure["milestone_best_hold_seconds"][FIRST_LEDGE.name], flush=True)
                elite = candidates[np.argsort(scores)[-2:]]
                mean, std = elite.mean(axis=0), np.maximum(elite.std(axis=0), 10)
        report["bounded_search"] = {"candidates": 24, "ticks_per_candidate_max": 600, "frame_skip": args.frame_skip,
                                    "history": history, "best_knots": best_knots.tolist()}
        # Validate any search result on the uncached reference, not just the fast worker.
        with make_bridge("reference", "selenium") as bridge:
            start = bridge.reset(42)
            commands = search_commands(best_knots)
            trace = bridge.step_commands(commands)
            if trace and not trace[-1]["dead"]:
                trace += bridge.step_commands([{**commands[-1], "id": ticks + i + 1} for i in range(120)])
            report["search_reference_replay"] = metrics(start, trace)
            (output / "search_reference_replay.json").write_text(
                json.dumps({"start": start, "trace": trace}), encoding="utf-8")
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
