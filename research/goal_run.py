"""One fresh admitted goal-SAC seed: one simulator, learned-only final reference gate."""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import torch
from stable_baselines3 import SAC

from research.demonstrations import require
from research.goal_env import GoalEnv, schema
from research.goal_execution import load_permit
from research.goal_train import TickBudget, train_seed, verify_checkpoint, SpacesOnly
from research.goal_evaluation import evaluate, validate_evaluation
from research.goal_study import plan, SEEDS
from research.provenance import fingerprint


def admission_result(evaluation, training):
    # A partial cap-stopped learner is still saved and evaluated, but cannot
    # promote the seed or silently start the next one.
    return {**evaluation, "physical_gate_passed": evaluation["pilot_gate_passed"],
            "pilot_gate_passed": bool(training["complete"] and evaluation["pilot_gate_passed"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-training", action="store_true")
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    permit, preflight_ticks = load_permit(args)
    from research.phase_controller import load_prior
    from research.fast_bridge import FastBridge
    from research.browser_bridge import BrowserBridge
    from research.env import RealGettingOverItEnv
    from research.study_metrics import enable_platform_support
    import stable_baselines3
    current = fingerprint()
    observations, opening, rms = load_prior(args.prior, current)
    from research.goal_demo import DemoActionMatcher
    from research.goal_study import DEMO_BURST_START, DEMO_BURST_TICKS, DEMO_MATCH_THRESHOLD
    demo = DemoActionMatcher(observations, opening, rms, DEMO_MATCH_THRESHOLD)
    # All preflight physics is conservatively charged to the first seed.
    budget = TickBudget(initial={"preflight": int(preflight_ticks)})
    output = args.output_dir
    training = output/"training"
    output.mkdir(parents=True, exist_ok=False)
    (output/"manifest.json").write_text(json.dumps({"version": "goal-pilot-run-v1", "seed": args.seed,
        "plan": plan(), "schema": schema(), "provenance": current,
        "admission": permit.payload["ticket"], "python": platform.python_version(), "numpy": np.__version__,
        "torch": torch.__version__, "stable_baselines3": stable_baselines3.__version__}, indent=2))
    def guard():
        permit.verify(args.seed)
    with FastBridge(headless=True) as bridge:
        budget.add("bridge_bootstrap", bridge.read_state()["tick"])
        raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True, frame_skip=1, horizon=2400)
        enable_platform_support(raw)
        env = GoalEnv(raw, budget=budget)
        model, targets, summary = train_seed(env, opening, args.seed, training, guard=guard,
                                             demo=demo, demo_burst_start=DEMO_BURST_START,
                                             demo_burst_ticks=DEMO_BURST_TICKS)
        env.close()
    checkpoint = training/summary["checkpoint"]
    saved = verify_checkpoint(checkpoint)
    require(saved["provenance"]["source_sha256"] == current["source_sha256"], "Saved policy source drift")
    torch.set_num_threads(1)
    loaded = SAC.load(checkpoint/"model.zip", env=SpacesOnly(), device="cpu")
    probe = np.zeros((16, 620), np.float32)
    require(np.array_equal(model.predict(probe, deterministic=True)[0],
                           loaded.predict(probe, deterministic=True)[0]), "Saved closed-loop actor reload drift")
    (output/"supervisor.json").write_text(json.dumps({"version": "stable-waypoint-v1", "waypoints": targets}, indent=2))
    with BrowserBridge(driver="selenium", headless=True) as reference:
        budget.add("bridge_bootstrap", reference.read_state()["tick"])
        result = evaluate(loaded, reference, targets, budget, output/"evaluation", guard=guard)
    validate_evaluation(output/"evaluation")
    result = admission_result(result, summary)
    result.update(seed=args.seed, physics=budget.record(), checkpoint=summary["checkpoint"],
                  training_summary=summary, saved_reload_exact=True, original_start=True,
                  final_goal_verified=False)
    (output/"result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"seed": args.seed, "first_ledge": result["first_ledge_successes"],
                      "nominal_height180": result["nominal_height180_hold90"], "pilot_pass": result["pilot_gate_passed"],
                      "deaths": result["deaths"], "summits": result["summits"], "physics": budget.total}))


if __name__ == "__main__":
    main()
