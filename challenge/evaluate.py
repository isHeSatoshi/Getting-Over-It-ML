"""Evaluate a policy against the challenge contract.

A submission provides a policy: any callable that maps one observation to one
legal action. This module runs it on the reference (uncached, fully rendered)
worker over the public cases and writes a signed-style report.

Usage:
    python -m challenge.evaluate --policy my_policy:Policy --out reports/run1
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from challenge.env import GettingOverItChallengeEnv
from challenge.tiers import (BASELINE, SCORING, STANDARD_CASES, TIER_REGIONS,
                             gate_report, holdout_cases)


class PolicyError(RuntimeError):
    pass


def load_policy(spec):
    """Import `module:Attribute`. The attribute must be callable."""
    if ":" not in spec:
        raise PolicyError("Use --policy module:Attribute")
    module_name, attribute = spec.split(":", 1)
    import importlib
    module = importlib.import_module(module_name)
    try:
        factory = getattr(module, attribute)
    except AttributeError as error:
        raise PolicyError(f"{module_name} has no {attribute}") from error
    return factory() if callable(factory) and not hasattr(factory, "action") else factory


def perturb(action, case, rng):
    action = np.asarray(action, dtype=np.float32)
    if case.action_noise_std:
        action = action + rng.normal(0, case.action_noise_std, action.shape)
    return np.clip(action, -1, 1).astype(np.float32)


def run_case(env, policy, case, max_decisions):
    rng = np.random.default_rng(case.noise_seed)
    observation, info = env.reset(seed=case.reset_seed)
    decision = 0
    for warmup in case.warmup:
        if decision >= max_decisions:
            break
        action = perturb(np.asarray(warmup, dtype=np.float32), case, rng)
        observation, _, terminated, truncated, info = env.step(action)
        decision += 1
        if terminated or truncated:
            break
    if hasattr(policy, "reset"):
        policy.reset()
    while decision < max_decisions:
        action = perturb(policy.action(observation), case, rng)
        observation, reward, terminated, truncated, info = env.step(action)
        decision += 1
        if terminated or truncated:
            break
    regions = info.get("region_success", {})
    return {
        "case": case.name,
        "public": case.public,
        "decisions": decision,
        "retained_gain": env.retained_gain,
        "episode_high_y": info.get("episode_high_y"),
        "success": info.get("success", False),
        "dead": info.get("dead", False),
        "region_success": regions,
        "region_best_hold_seconds": info.get("region_best_hold_seconds", {}),
        "tier_reached": max(
            (i for i, r in enumerate(TIER_REGIONS)
             if regions.get(r.name)), default=-1),
    }


def evaluate(policy, backend="reference", driver="selenium", max_decisions=1800,
             cases=STANDARD_CASES):
    from research.backends import make_bridge
    started = time.time()
    with make_bridge(backend, driver) as bridge:
        env = GettingOverItChallengeEnv(bridge=bridge)
        results = [run_case(env, policy, case, max_decisions) for case in cases]
        env.close()
    passes = [r for r in results if r["region_success"].get("tier0_settled_ground")]
    summary = {
        "cases": len(results),
        "tier0_passed": len(passes),
        "tier0_fraction": len(passes) / len(results) if results else 0.0,
        "mean_retained_gain": float(np.mean([r["retained_gain"] for r in results]))
        if results else 0.0,
        "deaths": sum(1 for r in results if r["dead"]),
        "summits": sum(1 for r in results if r["success"]),
        "best_tier": max((r["tier_reached"] for r in results), default=-1),
        "wall_seconds": round(time.time() - started, 2),
    }
    return {"summary": summary, "results": results,
            "baseline": BASELINE, "scoring": SCORING}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, help="module:Attribute")
    parser.add_argument("--out", required=True, help="report directory")
    parser.add_argument("--backend", default="reference", choices=("reference", "fast"))
    parser.add_argument("--max-decisions", type=int, default=1800)
    parser.add_argument("--holdout", action="store_true",
                        help="also run the unpublished holdout cases")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    report = evaluate(policy, backend=args.backend, max_decisions=args.max_decisions)
    if args.holdout:
        report["holdout"] = evaluate(policy, backend=args.backend,
                                     max_decisions=args.max_decisions,
                                     cases=holdout_cases())
        hold = report["holdout"]["summary"]
        report["gates"] = gate_report(
            report["summary"]["tier0_fraction"],
            hold["tier0_fraction"],
            report["summary"]["deaths"],
            report["summary"]["summits"] > 0,
            hold["cases"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report.get("summary", {}), indent=2))
    if "gates" in report:
        print("GATES", json.dumps(report["gates"], indent=2))
    print("Report:", (out / "report.json").resolve())


if __name__ == "__main__":
    main()
