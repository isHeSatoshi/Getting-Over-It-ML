"""Read-only physical goal metrics from contract-validated campaign artifacts."""
import argparse
import json
import math
from pathlib import Path

from research.campaign import aggregate


def goal_metrics(summary, template):
    expected_seeds = set(template["training_seeds"])
    cohorts = {}
    seen = set()
    for row in summary["rows"]:
        identity = (row["variant"], row["seed"])
        if identity in seen:
            raise ValueError("Duplicate training seed in goal evidence")
        seen.add(identity)
        for key in ("success_rate", "full_climb_success_rate"):
            value = row["after"][key]
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Invalid physical success fraction")
        cohorts.setdefault(row["variant"], []).append(row)
    candidates = []
    for variant, rows in cohorts.items():
        if (len(expected_seeds) < 3 or {row["seed"] for row in rows} != expected_seeds
                or any(row["after"]["cases"] != len(template["fixed"]["evaluation_cases"])
                       for row in rows)):
            continue
        candidates.append({
            "variant": variant,
            "training_seeds": sorted(expected_seeds),
            "worst_seed_reference_completion_rate": min(
                row["after"]["full_climb_success_rate"] for row in rows),
            "worst_seed_first_ledge_rate": min(row["after"]["success_rate"] for row in rows),
            "nominal_completion_every_seed": all(
                row["after"]["nominal_full_climb_success"] for row in rows),
            "reference_deaths": sum(row["after"]["falls"] for row in rows),
            "median_retained_gain_each_seed": {
                str(row["seed"]): row["after"]["median_retained_gain"] for row in rows},
        })
    best = max(candidates, key=lambda item: (
        item["worst_seed_reference_completion_rate"],
        item["nominal_completion_every_seed"],
        item["worst_seed_first_ledge_rate"],
        -item["reference_deaths"]), default=None)
    rate = best["worst_seed_reference_completion_rate"] if best else 0.0
    return {
        "worst_seed_reference_completion_rate": rate,
        "candidate_goal_passed": bool(
            best and rate >= 0.8 and best["nominal_completion_every_seed"]),
        "final_goal_verified": False,
        "best_complete_variant": best,
        "completed_runs": len(summary["rows"]),
        "missing_runs": summary["missing_runs"],
        "warning": "A candidate still needs independent held-out reference evaluation, "
                   "upper-route fidelity, and a replayable saved-policy package. "
                   "Structured cases are not IID trials.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    if not args.directory.is_absolute():
        parser.error("Pass an absolute campaign artifact directory")
    summary = aggregate(args.directory)
    campaign = json.loads((args.directory / "campaign.json").read_text(encoding="utf-8"))
    metrics = goal_metrics(summary, campaign["plan"])
    print(json.dumps(metrics, indent=2))
    for name in ("worst_seed_reference_completion_rate", "completed_runs"):
        print(f"METRIC {name}={metrics[name]}")


if __name__ == "__main__":
    main()
