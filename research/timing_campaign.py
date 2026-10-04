"""Prepare/check a distinct timing study. This module cannot launch jobs."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import numpy as np

from research.browser_bridge import ROOT
from research.campaign import aggregate as pilot_aggregate, digest
from research.case_clock import PhysicalCaseClock
from research.evaluation_cases import STANDARD_CASES
from research.optimizer_work import WORK_VERSION
from research.provenance import fingerprint
from research.reward import DEATH_Y, SUCCESS_Y, RewardConfig
from research.study_metrics import benchmark_contract
from research.timing_study import plan as study_plan
from research.training_timing import training_settings

VERSION = "timing-campaign-v1"
PROVENANCE_KEYS = ("project_sha256", "runtime_sha256", "asset_set_sha256", "source_sha256")
METRIC_NAMES = tuple(item["name"] for item in benchmark_contract(True))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def contract():
    study = study_plan()
    runs = [{"name": f"{arm['name']}_seed_{seed}", "seed": seed, "arm": arm["name"],
             "frame_skip": arm["frame_skip"], "steps": arm["transitions"]}
            for seed in study["training_seeds"] for arm in study["arms"]]
    return json.loads(json.dumps({
        "version": VERSION, "study": study, "runs": runs,
        "run_order": "Sequential paired timing arms within seeds 3,4,5; no concurrency",
        "admission": "Prepared only. No runner, budget or preflight launch admission.",
    }))


def command(run, output, smoke=False):
    require(type(smoke) is bool and run in contract()["runs"], "Undeclared timing run")
    output = Path(output)
    require(output.is_absolute() and not output.exists(), "Use a new absolute run directory")
    repeat = run["frame_skip"]
    # Full commands are plans only: research.train still refuses remote timing
    # execution until a separately tested bounded runner admits the session.
    return [sys.executable, "-m", "research.train", "--algorithm", "ppo", "--action", "absolute",
            "--backend", "fast", "--timing-study", "--frame-skip", str(repeat),
            "--seed", str(run["seed"]), "--steps", str(256 // repeat if smoke else run["steps"]),
            "--evaluation-suite", "standard", "--evaluation-decisions", str(1800 // repeat),
            "--reward-profile", "settled", "--discount-half-life", "120",
            "--replay-buffer-size", "200000", "--output-dir", str(output),
            "--smoke" if smoke else "--remote-training"]


def prepare(directory, pilot_directory):
    directory, pilot_directory = Path(directory), Path(pilot_directory)
    require(directory.is_absolute() and pilot_directory.is_absolute(), "Use absolute artifact paths")
    require(not directory.exists(), "Refusing to overwrite a study directory")
    prior = pilot_aggregate(pilot_directory)
    require(not prior["missing_runs"] and len(prior["rows"]) == 9
            and not prior["followup_eligible_variants"] and not prior["scale_eligible_variants"],
            "Timing diagnostic requires a complete pilot with no eligible variant")
    prior_campaign = json.loads((pilot_directory / "campaign.json").read_text(encoding="utf-8"))
    record = {"contract": contract(), "provenance": fingerprint(),
              "prior_pilot": {"summary_sha256": digest(prior),
                              "provenance": prior_campaign["provenance"],
                              "complete_ineligible_runs": len(prior["rows"])},
              "activation": "No jobs launched or reserved; worker/budget/preflight admission remains required"}
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "timing_campaign.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def summarize_evaluation(records, repeat, decisions):
    require(type(repeat) is int and repeat in (1, 4) and integer(decisions, 1),
            "Invalid declared evaluation timing")
    expected = {case.name: case for case in STANDARD_CASES}
    require(len(records) == len(expected) and {row["case"]["name"] for row in records} == set(expected),
            "Missing, duplicate or changed evaluation cases")
    totals = {name: 0 for name in METRIC_NAMES}
    retained, completions, falls, actual_ticks = [], 0, 0, 0
    nominal_completion = False
    for record in records:
        case = expected[record["case"]["name"]]
        require(record["case"] == json.loads(json.dumps(case.describe()))
                and record["seed"] == case.reset_seed, "Changed legal perturbation/reset contract")
        require(record["timing_contract"] == {
            "version": "physical-case-evaluation-v1", "frame_skip": repeat,
            "physics_hz": 30.0, "perturbation_hold_ticks": 4,
            "requested_physics_ticks": decisions * repeat}, "Changed physical evaluation clock")
        trace = record["trace"]
        require(integer(record["decisions"], 1) and record["decisions"] == len(trace)
                and len(trace) <= decisions and record["final"] == trace[-1],
                "Invalid trace length or pre-reset final record")
        clock, elapsed, latched = PhysicalCaseClock(case), 0, set()
        hold_times, spawn_y = {}, None
        for index, row in enumerate(trace):
            ticks = row["physics_ticks"]
            require(integer(ticks, 1) and ticks <= repeat, "Invalid actual evaluation ticks")
            require(row["backend"] == "turbowarp-real-renderer", "Wrong evaluation physics backend")
            require(all(type(row[key]) is bool for key in ("success", "dead")), "Invalid outcome flags")
            y = row["player_world_y"]
            require(finite(y) and row["success"] == (y > SUCCESS_Y)
                    and row["dead"] == (y < DEATH_Y), "Outcome disagrees with original world height")
            terminal = row["success"] or row["dead"]
            require(not terminal or index == len(trace) - 1, "Trace continues after terminal outcome")
            require(ticks == repeat or terminal, "Short step without terminal outcome")
            for key in ("body_hit_frames", "hammer_hit_frames"):
                require(integer(row[key]) and row[key] <= ticks, "Invalid contact tick counts")
            for key in ("action", "applied_action"):
                values = row[key]
                require(len(values) == 2 and all(finite(value) and abs(value) <= 1 for value in values),
                        "Invalid legal normalized action")
            applied = clock.apply(np.asarray([row["action"]], dtype=np.float32), elapsed)[0].tolist()
            require(applied == row["applied_action"], "Applied action differs from declared physical perturbation")
            elapsed += ticks
            require(row["milestone_contract"] == benchmark_contract(True), "Changed central/secondary metrics")
            flags, times = row["milestone_success"], row["milestone_success_seconds"]
            require(set(flags) == set(METRIC_NAMES) and set(times) == set(METRIC_NAMES)
                    and all(type(value) is bool for value in flags.values()), "Invalid physical metric flags")
            now = {name for name, passed in flags.items() if passed}
            require(latched <= now, "A latched hold disappeared")
            latched = now
            for name in METRIC_NAMES:
                require((finite(times[name]) and 3 <= times[name] <= elapsed / 30 + 1e-9)
                        if flags[name] else times[name] is None, "Invalid physical hold time")
                if flags[name]:
                    require(name not in hold_times or hold_times[name] == times[name],
                            "Latched physical hold time changed")
                    hold_times[name] = times[name]
            require(finite(row["retained_gain"]), "Non-finite retained altitude")
            origin = y - row["retained_gain"]
            require(15 <= origin <= 30 and (spawn_y is None or math.isclose(
                origin, spawn_y, rel_tol=0, abs_tol=1e-7)), "Retained altitude has a changed spawn origin")
            spawn_y = origin
        final = record["final"]
        require(final["success"] or final["dead"] or len(trace) == decisions,
                "Nonterminal evaluation ended before its declared horizon")
        require(integer(record["controlled_physics_ticks"], 1)
                and record["controlled_physics_ticks"] == elapsed
                and record["reset_settling_physics_ticks"] == 240,
                "Controlled/reset evaluation work disagrees with trace")
        for name in METRIC_NAMES:
            totals[name] += int(final["milestone_success"][name])
        completions += int(final["success"])
        falls += int(final["dead"])
        retained.append(final["retained_gain"])
        actual_ticks += elapsed
        if case.name == "nominal":
            nominal_completion = final["success"]
    return {"cases": len(records), "holds": totals,
            "hold_rates": {name: value / len(records) for name, value in totals.items()},
            "full_completions": completions, "full_completion_rate": completions / len(records),
            "nominal_full_completion": nominal_completion, "deaths": falls,
            "median_retained_gain": sorted(retained)[len(retained) // 2],
            "controlled_physics_ticks": actual_ticks,
            "reset_settling_physics_ticks": 240 * len(records)}


def validate_run(manifest, training, evaluation, run, provenance):
    require(run in contract()["runs"], "Undeclared timing run")
    repeat, steps = run["frame_skip"], run["steps"]
    timing = training_settings("ppo", False, frame_skip=repeat, timing_study=True)
    config = manifest["config"]
    require(manifest["purpose"] == "remote research run" and config["smoke"] is False
            and config["remote_training"] is True and config["timing_study"] is True,
            "Smoke or unadmitted run type cannot count as study evidence")
    for key, value in {"algorithm": "ppo", "action": "absolute", "seed": run["seed"],
                       "frame_skip": repeat, "steps": steps, "backend": "fast",
                       "reward_profile": "settled", "discount_half_life": 120,
                       "evaluation_decisions": timing["evaluation_decisions"],
                       "evaluation_suite": "standard", "replay_buffer_size": 200000}.items():
        require(config[key] == value, "Changed run setting: " + key)
    require(config["no_terrain"] is False and manifest["device"] == "cpu", "Changed observation/device contract")
    for key in PROVENANCE_KEYS:
        require(manifest[key] == provenance[key], "Mixed source/game snapshot: " + key)
    versions = {key: manifest[key] for key in ("python", "numpy", "torch", "stable_baselines3")}
    require(all(isinstance(value, str) and value for value in versions.values()), "Missing dependency versions")
    require(manifest["steps"] == steps and manifest["control_timing_contract"] == timing
            and training["control_timing_contract"] == timing
            and manifest["reward_contract"] == RewardConfig().describe(repeat),
            "Changed reward/training physical-time contract")
    require(manifest["reward_normalization"] == {
        "enabled": False, "clipping": "disabled", "units": "raw_task_units"}, "Reward normalization changed")
    require(manifest["evaluation_contract"] == {
        "suite": "standard", "cases": json.loads(json.dumps([case.describe() for case in STANDARD_CASES])),
        "decisions": timing["evaluation_decisions"], "benchmarks": benchmark_contract(True)},
        "Changed reference evaluation declaration")
    require(training["complete"] is True and training["actual_transitions"] == steps
            and training["requested_transitions"] == steps
            and training["learner_gamma"] == timing["gamma"]
            and training["learner_gae_lambda"] == timing["gae_lambda"]
            and training["torch_threads"] == 1
            and finite(training["learning_wall_seconds"]) and training["learning_wall_seconds"] > 0,
            "Incomplete work or learner discount/GAE/thread mismatch")
    require(all(integer(training[key], 1) for key in (
        "actual_transitions", "requested_transitions", "torch_threads")),
        "Invalid learner work count types")
    optimizer = training["optimizer_work"]
    require(manifest["optimizer_work_contract"]["version"] == optimizer["version"] == WORK_VERSION
            and optimizer["algorithm"] == "ppo" and optimizer["optimizer_step_calls"] == {"policy": 3840}
            and optimizer["total_optimizer_step_calls"] == 3840
            and optimizer["sb3_internal_update_counter"] == 480, "Incorrect optimizer work units/counts")
    work = training["physical_work"]
    require(work["version"] == "controlled-reset-ticks-v1"
            and work["scope"] == "Training environment only; excludes preflight, evaluation and runtime boot"
            and work["frame_skip"] == repeat
            and work["decision_steps"] == steps
            and work["nominal_controlled_physics_ticks"] == steps * repeat,
            "Incorrect nominal training physical work")
    controlled, resets, reset_ticks, short = (
        work[key] for key in ("controlled_physics_ticks", "resets",
                             "reset_settling_physics_ticks", "terminal_short_decisions"))
    require(integer(controlled, steps) and controlled <= steps * repeat
            and integer(resets, steps // timing["episode_decisions"] + 1) and resets <= steps + 1
            and integer(reset_ticks) and reset_ticks == 120 * resets
            and integer(short) and short <= resets - 1
            and work["total_counted_physics_ticks"] == controlled + reset_ticks,
            "Inconsistent actual controlled/reset training work")
    deficit = steps * repeat - controlled
    require(short <= deficit <= short * (repeat - 1), "Terminal short-step count disagrees with actual exposure")
    require(evaluation["training_backend"] == "fast" and evaluation["evaluation_backend"] == "reference",
            "Evaluation must use the independent original reference")
    before = summarize_evaluation(evaluation["before"], repeat, timing["evaluation_decisions"])
    after = summarize_evaluation(evaluation["after"], repeat, timing["evaluation_decisions"])
    return {"run": run["name"], "arm": run["arm"], "seed": run["seed"],
            "frame_skip": repeat, "before": before, "after": after,
            "hold_rate_improvement": {name: after["hold_rates"][name] - before["hold_rates"][name]
                                      for name in METRIC_NAMES},
            "training_physical_work": work, "optimizer_work": optimizer,
            "learning_wall_seconds": training["learning_wall_seconds"], "dependencies": versions}


def aggregate(directory):
    directory = Path(directory)
    record = json.loads((directory / "timing_campaign.json").read_text(encoding="utf-8"))
    require(record["contract"] == contract(), "Timing-study protocol changed")
    rows, missing, dependency_versions = [], [], None
    for run in record["contract"]["runs"]:
        path = directory / "runs" / run["name"]
        required = ("manifest.json", "training_summary.json", "evaluation.json")
        absent = [filename for filename in required if not (path / filename).is_file()]
        if absent:
            missing.append({"run": run["name"], "files": absent})
            continue
        manifest, training, evaluation = (
            json.loads((path / filename).read_text(encoding="utf-8")) for filename in required)
        row = validate_run(manifest, training, evaluation, run, record["provenance"])
        if dependency_versions is None:
            dependency_versions = row["dependencies"]
        require(row["dependencies"] == dependency_versions, "Mixed learner dependency versions")
        rows.append(row)
    cohorts = []
    for arm in record["contract"]["study"]["arms"]:
        selected = [row for row in rows if row["arm"] == arm["name"]]
        complete = {row["seed"] for row in selected} == {3, 4, 5} and len(selected) == 3
        cohorts.append({
            "arm": arm["name"], "complete": complete, "completed_seeds": sorted(row["seed"] for row in selected),
            "worst_seed_hold_rates": {name: min(row["after"]["hold_rates"][name] for row in selected)
                                      if complete else None for name in METRIC_NAMES},
            "worst_seed_full_completion_rate": min(row["after"]["full_completion_rate"] for row in selected)
                                               if complete else None,
            "nominal_completion_every_seed": complete and all(row["after"]["nominal_full_completion"] for row in selected),
        })
    comparisons = {}
    if all(cohort["complete"] for cohort in cohorts):
        comparisons = {name: cohorts[0]["worst_seed_hold_rates"][name] - cohorts[1]["worst_seed_hold_rates"][name]
                       for name in METRIC_NAMES}
    return {"version": VERSION, "rows": rows, "missing_runs": missing, "cohorts": cohorts,
            "repeat_1_minus_repeat_4_worst_seed_hold_rate": comparisons,
            "decision": "diagnostic_complete_no_automatic_promotion" if not missing else "incomplete",
            "final_goal_verified": False, "large_scale_authorized": False,
            "binary_verification": "JSON-only checker; verify immutable final model/normalizer objects separately",
            "warning": "Nominal exposure is not actual exposure; equal calls are not equal FLOPs. "
                       "Structured cases are not IID trials; standard cases cannot verify the final goal."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--directory", type=Path)
    p.add_argument("--pilot-directory", type=Path, required=True)
    p = sub.add_parser("summarize")
    p.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory or ROOT / "artifacts" / (
        "timing_campaign_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    require(directory.is_absolute(), "Use an absolute campaign directory")
    if args.operation == "prepare":
        prepare(directory, args.pilot_directory)
        print("Prepared only, no jobs launched:", directory)
    else:
        print(json.dumps(aggregate(directory), indent=2))


if __name__ == "__main__":
    main()
