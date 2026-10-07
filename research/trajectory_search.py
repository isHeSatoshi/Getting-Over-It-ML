"""Small exact-game CEM baseline. Reset/replay, never incomplete VM snapshots.

This searches open-loop mouse trajectories. It is neither a trained policy nor
evidence of generalization; held-out replay and retained height are reported.
"""
import argparse
from datetime import datetime, timezone
import json
import math
import numpy as np

from research.browser_bridge import BrowserBridge, ROOT
from research.diagnose import summarize


def commands_from_knots(knots, ticks):
    times = np.linspace(0, ticks - 1, len(knots))
    x = np.interp(np.arange(ticks), times, knots[:, 0])
    y = np.interp(np.arange(ticks), times, knots[:, 1])
    return [{"x": float(x[i]), "y": float(y[i]), "id": i + 1} for i in range(ticks)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", default="auto", choices=["auto", "embedded", "selenium"])
    parser.add_argument("--population", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--ticks", type=int, default=360)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if not (4 <= args.population <= 16 and 1 <= args.iterations <= 5 and 120 <= args.ticks <= 600):
        parser.error("This baseline is deliberately bounded")
    rng = np.random.default_rng(args.seed)
    n_knots = 19
    angles = -np.linspace(0, (args.ticks - 1) * math.pi / 60, n_knots)
    mean = np.stack([90 * np.cos(angles), 90 * np.sin(angles)], axis=1)
    std = np.full_like(mean, 35.0)
    output = ROOT / "artifacts" / ("search_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    history, best, best_score = [], mean.copy(), -math.inf
    with BrowserBridge(driver=args.driver) as bridge:
        for iteration in range(args.iterations):
            population = np.clip(rng.normal(mean, std, size=(args.population, *mean.shape)), -128, 128)
            population[0] = best if iteration else mean
            scores = []
            for candidate, knots in enumerate(population):
                start = bridge.reset(args.seed)
                trace = bridge.step_commands(commands_from_knots(knots, args.ticks))
                metrics = summarize(start, trace)
                # Score the last second, not a transient jump, and include a
                # small lateral exploration tie-breaker. These are *search*
                # heuristics, not the RL task reward.
                tail = trace[-min(60, len(trace)):]
                retained = float(np.mean([s["player_world_y"] for s in tail])) - start["player_world_y"]
                score = retained + 0.02 * max(0, metrics["end_x"]) - 200 * metrics["dead"]
                scores.append(score)
                history.append({"iteration": iteration, "candidate": candidate, "score": score,
                                **metrics, "knots": knots.tolist()})
                with (output / "candidates.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json.dumps(history[-1]) + "\n")
                if score > best_score:
                    best_score, best = score, knots.copy()
                print(iteration, candidate, "score", round(score, 2), "max/retained",
                      round(metrics["max_gain"], 2), round(metrics["retained_gain"], 2), flush=True)
            elites = population[np.argsort(scores)[-max(2, args.population // 4):]]
            mean = elites.mean(axis=0)
            std = np.maximum(elites.std(axis=0), 10)
        replay = []
        best_commands = commands_from_knots(best, args.ticks)
        for seed in (1001, 1002, 1003):
            start = bridge.reset(seed)
            trace = bridge.step_commands(best_commands)
            hold = bridge.step_commands([
                {"x": best_commands[-1]["x"], "y": best_commands[-1]["y"], "id": args.ticks + i + 1}
                for i in range(120)])
            replay.append({"seed": seed, **summarize(start, trace),
                           "retained_gain_after_hold": (hold[-1] if hold else trace[-1])["player_world_y"] - start["player_world_y"]})
        (output / "best_trace.json").write_text(
            json.dumps({"start": start, "commands": best_commands, "trace": trace, "hold_trace": hold}), encoding="utf-8")
    (output / "search.json").write_text(
        json.dumps({"config": vars(args), "history": history, "held_out_replay": replay,
                    "best_knots": best.tolist()}, indent=2), encoding="utf-8")
    print("Held-out replay:", json.dumps(replay))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
