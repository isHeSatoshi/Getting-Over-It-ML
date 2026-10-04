"""Prepare/check the nine-run imitation comparison. No execution entrypoint."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


from research.behavior_cloning import VERSION as CLONING_VERSION
from research.campaign import digest
from research.demonstrations import load, require
from research.imitation_study import plan
from research.imitation_train import settings
from research.optimizer_work import WORK_VERSION
from research.provenance import fingerprint
from research.reward import RewardConfig
from research.timing_campaign import (
    METRIC_NAMES, PROVENANCE_KEYS, aggregate as timing_aggregate,
    finite, integer, summarize_evaluation)

VERSION = "imitation-campaign-v1"


def contract():
    study = plan()
    return json.loads(json.dumps({
        "version": VERSION, "study": study,
        "runs": [{"name": f"{arm}_seed_{seed}", "arm": arm, "seed": seed}
                 for seed in study["training_seeds"] for arm in study["arms"]],
        "run_order": "Sequential three arms within each seed 6,7,8",
        "admission": "Preparation only; full trainer and worker admission remain required",
    }))


def dataset_contract(directory, current):
    arrays, record = load(directory, current)
    require([episode["case"] for episode in record["episodes"]] == contract()["study"]["data"]["cases"],
            "Missing or changed declared training demonstration streams")
    require(all(type(episode["controlled_ticks"]) is int
                and episode["controlled_ticks"] == 600
                and episode["reset_settling_ticks"] == 120
                and episode["final"]["milestone_contract"] == plan()["evaluation"]["benchmarks"]
                for episode in record["episodes"]),
            "Changed expert collection horizon/reset/metric contract")
    eligible = arrays["eligible"]
    require(eligible.any(), "No eligible physically held training demonstrations")
    observations = arrays["observations"][eligible]
    return {"data_sha256": record["data_sha256"],
            "expert_source_sha256": record["expert_source_sha256"],
            "samples": record["samples"], "eligible_samples": int(eligible.sum()),
            "normalization_contract": {
                "source": "Eligible training demonstrations only", "samples": len(observations),
                "raw_observations_sha256": hashlib.sha256(observations.tobytes()).hexdigest(),
                "frozen": True, "clip_obs": 10.0, "epsilon": 1e-8}}


def prepare(directory, timing_directory, dataset_directory):
    directory, timing_directory, dataset_directory = map(
        Path, (directory, timing_directory, dataset_directory))
    require(all(path.is_absolute() for path in (directory, timing_directory, dataset_directory))
            and not directory.exists(), "Use new absolute campaign and input directories")
    prior = timing_aggregate(timing_directory)
    require(not prior["missing_runs"] and len(prior["rows"]) == 6
            and all(cohort["complete"] and cohort["worst_seed_hold_rates"]["first_ledge_v1"] < 8 / 9
                    for cohort in prior["cohorts"]),
            "Imitation proposal requires complete timing results without robust retention")
    current = fingerprint()
    data = dataset_contract(dataset_directory, current)
    record = {"contract": contract(), "provenance": current, "dataset": data,
              "prior_timing_summary_sha256": digest(prior),
              "activation": "No jobs launched/reserved; remote preflight/admission required"}
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "imitation_campaign.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def command(run, output, dataset, smoke=False):
    output, dataset = Path(output), Path(dataset)
    require(run in contract()["runs"] and type(smoke) is bool
            and output.is_absolute() and dataset.is_absolute() and not output.exists(),
            "Use a declared run, new absolute output and absolute trusted dataset")
    return [sys.executable, "-m", "research.imitation_train", "--arm", run["arm"],
            "--seed", str(run["seed"]), "--dataset", str(dataset),
            "--output-dir", str(output), "--smoke" if smoke else "--remote-training"]


def validate_run(manifest, training, evaluation, run, campaign):
    require(run in contract()["runs"], "Undeclared imitation run")
    timing = settings(run["arm"], False)
    config = manifest["config"]
    require(manifest["version"] == timing["version"]
            and manifest["purpose"] == "remote imitation research run"
            and config["smoke"] is False and config["remote_training"] is True,
            "Smoke or unadmitted artifacts cannot establish imitation study results")
    require(config["arm"] == run["arm"] and type(config["seed"]) is int
            and config["seed"] == run["seed"]
            and manifest["settings"] == training["settings"] == timing,
            "Changed arm/seed or declared training settings")
    admission = manifest.get("imitation_admission")
    require(isinstance(admission, dict)
            and admission.get("version") == "imitation-execution-admission-v1"
            and isinstance(admission.get("session"), str) and admission["session"].startswith("imitation-")
            and admission.get("run") == run["name"] and finite(admission.get("deadline_epoch"))
            and admission["deadline_epoch"] > 0
            and isinstance(admission.get("source_space_revision"), str)
            and len(admission["source_space_revision"]) == 40
            and all(c in "0123456789abcdef" for c in admission["source_space_revision"])
            and admission.get("dataset_sha256") == campaign["dataset"]["data_sha256"],
            "Missing/mixed source/dataset execution admission")
    for key in PROVENANCE_KEYS:
        require(manifest[key] == campaign["provenance"][key], "Mixed imitation source/assets: " + key)
    require(manifest["dataset_sha256"] == campaign["dataset"]["data_sha256"]
            and manifest["normalization_contract"] == campaign["dataset"]["normalization_contract"]
            and manifest["normalization_contract"]["frozen"] is True
            and type(manifest["normalization_contract"]["samples"]) is int,
            "Changed training corpus or common frozen normalization")
    require(manifest["reward_contract"] == RewardConfig().describe(1)
            and manifest["reward_normalization"] == {
                "enabled": False, "clipping": "disabled", "units": "raw_task_units"}
            and manifest["device"] == "cpu",
            "Changed raw reward/discount/device contract")
    require(manifest["environment_contract"] == {
        "action_mode": "absolute", "terrain": True, "frame_skip": 1, "physics_hz": 30.0,
        "ordinary_start": True, "privileged_resets": False},
        "Changed legal ordinary-start environment contract")
    require(manifest["evaluation_contract"] == {
        "cases": contract()["study"]["evaluation"]["cases"],
        "benchmarks": contract()["study"]["evaluation"]["benchmarks"]},
        "Changed legal reference evaluation declaration")
    versions = {key: manifest[key] for key in ("python", "numpy", "torch", "stable_baselines3")}
    require(all(isinstance(value, str) and value for value in versions.values()),
            "Missing dependency versions")
    require(training["complete"] is True and training["normalization_unchanged"] is True
            and type(training["torch_threads"]) is int and training["torch_threads"] == 1
            and training["learner_gamma"] == timing["gamma"]
            and training["learner_gae_lambda"] == timing["gae_lambda"],
            "Incomplete training, changed frozen RMS/discount/GAE/threads")
    clone = training["cloning"]
    if not timing["cloning_updates"]:
        require(clone is None and evaluation["after_cloning"] is None, "Scratch arm contains cloning")
    else:
        require(isinstance(clone, dict) and clone["version"] == CLONING_VERSION
                and clone["purpose"] == "Admitted remote actor demonstration warm start"
                and type(clone["optimizer_step_calls"]) is int
                and clone["optimizer_step_calls"] == timing["cloning_updates"]
                and all(type(clone[key]) is int for key in (
                    "batch_size", "sample_presentations", "samples", "rl_transitions"))
                and clone["batch_size"] == timing["cloning_batch_size"]
                and clone["sample_presentations"] == timing["cloning_updates"] * timing["cloning_batch_size"]
                and clone["learning_rate"] == timing["cloning_learning_rate"]
                and clone["samples"] == campaign["dataset"]["eligible_samples"]
                and type(clone["seed"]) is int and clone["seed"] == run["seed"]
                and clone["rl_transitions"] == 0 and clone["ppo_optimizer_state_preserved"] is True
                and all(finite(clone[key]) and clone[key] >= 0 for key in (
                    "mean_squared_action_error_before", "mean_squared_action_error_after", "wall_seconds")),
                "Changed cloning work, data, initialization or supervised diagnostics")
    steps = timing["rl_transitions"]
    require(type(training["rl_transitions"]) is int and training["rl_transitions"] == steps
            and finite(training["learning_wall_seconds"])
            and (training["learning_wall_seconds"] > 0 if steps else training["learning_wall_seconds"] >= 0),
            "Changed RL budget or learning wall time")
    optimizer = training["optimizer_work"]
    calls, internal = (3840, 480) if steps else (0, 0)
    require(optimizer["version"] == WORK_VERSION and optimizer["algorithm"] == "ppo"
            and optimizer["optimizer_step_calls"] == {"policy": calls}
            and type(optimizer["optimizer_step_calls"]["policy"]) is int
            and type(optimizer["total_optimizer_step_calls"]) is int
            and optimizer["total_optimizer_step_calls"] == calls
            and type(optimizer["sb3_internal_update_counter"]) is int
            and optimizer["sb3_internal_update_counter"] == internal,
            "Incorrect PPO optimizer work")
    work = training["physical_work"]
    require(work["version"] == "controlled-reset-ticks-v1"
            and work["scope"] == "Training environment only; excludes preflight, evaluation and runtime boot"
            and type(work["frame_skip"]) is int and work["frame_skip"] == 1
            and type(work["decision_steps"]) is int and work["decision_steps"] == steps
            and type(work["controlled_physics_ticks"]) is int
            and type(work["nominal_controlled_physics_ticks"]) is int
            and work["nominal_controlled_physics_ticks"] == work["controlled_physics_ticks"] == steps
            and type(work["terminal_short_decisions"]) is int and work["terminal_short_decisions"] == 0,
            "Changed controlled physics or shortened-step accounting")
    resets, reset_ticks = work["resets"], work["reset_settling_physics_ticks"]
    require(integer(resets) and integer(reset_ticks)
            and ((steps // timing["episode_decisions"] + 1 <= resets <= steps + 1)
                 if steps else resets == 0)
            and reset_ticks == 120 * resets and work["total_counted_physics_ticks"] == steps + reset_ticks,
            "Inconsistent controlled/reset exposure")
    require(evaluation["evaluation_backend"] == "reference"
            and evaluation["training_backend"] == "fast", "Wrong original reference/training backend")
    before = summarize_evaluation(evaluation["untrained"], 1, 1800)
    after_clone = (summarize_evaluation(evaluation["after_cloning"], 1, 1800)
                   if clone is not None else None)
    final = summarize_evaluation(evaluation["final"], 1, 1800)
    if not steps:
        require(evaluation["final"] == evaluation["after_cloning"],
                "BC-only final trace differs despite zero RL work")
    nominal = next(r for r in evaluation["final"] if r["case"]["name"] == "nominal")
    return {"run": run["name"], "arm": run["arm"], "seed": run["seed"],
            "before": before, "after_cloning": after_clone, "after": final,
            "nominal_central_hold": nominal["final"]["milestone_success"]["first_ledge_v1"],
            "untrained_trace_sha256": digest(evaluation["untrained"]),
            "after_cloning_trace_sha256": digest(evaluation["after_cloning"]) if clone else None,
            "training_physical_work": work, "optimizer_work": optimizer, "cloning_work": clone,
            "dependencies": versions, "learning_wall_seconds": training["learning_wall_seconds"],
            "admission": {key: value for key, value in admission.items() if key != "run"}}


def aggregate(directory):
    directory = Path(directory)
    record = json.loads((directory / "imitation_campaign.json").read_text(encoding="utf-8"))
    require(record["contract"] == contract(), "Imitation campaign protocol changed")
    rows, missing, versions, admission = [], [], None, None
    for run in contract()["runs"]:
        path = directory / "runs" / run["name"]
        required = ("manifest.json", "training_summary.json", "evaluation.json")
        absent = [name for name in required if not (path / name).is_file()]
        if absent:
            missing.append({"run": run["name"], "files": absent})
            continue
        row = validate_run(*(json.loads((path / name).read_text(encoding="utf-8"))
                             for name in required), run, record)
        if versions is None:
            versions, admission = row["dependencies"], row["admission"]
        require(row["dependencies"] == versions and row["admission"] == admission,
                "Mixed dependency versions or admitted sessions")
        if record.get("execution_admission") is not None:
            require(row["admission"] == record["execution_admission"], "Changed claimed execution admission")
        rows.append(row)
    for seed in plan()["training_seeds"]:
        selected = [row for row in rows if row["seed"] == seed]
        require(len({row["untrained_trace_sha256"] for row in selected}) <= 1,
                "Matched-seed initial reference behavior differs")
        clones = [row["after_cloning_trace_sha256"] for row in selected if row["cloning_work"]]
        require(len(set(clones)) <= 1, "Matched-seed cloned checkpoint behavior differs")
    cohorts = []
    for arm in plan()["arms"]:
        selected = [row for row in rows if row["arm"] == arm]
        complete = len(selected) == 3 and {row["seed"] for row in selected} == {6, 7, 8}
        cohorts.append({"arm": arm, "complete": complete,
                        "completed_seeds": sorted(row["seed"] for row in selected),
                        "worst_seed_hold_rates": {name: min(r["after"]["hold_rates"][name] for r in selected)
                                                  if complete else None for name in METRIC_NAMES},
                        "worst_seed_full_completion_rate": min(r["after"]["full_completion_rate"] for r in selected)
                                                           if complete else None,
                        "first_skill_candidate": complete and all(r["nominal_central_hold"]
                            and r["after"]["hold_rates"]["first_ledge_v1"] >= 8 / 9 for r in selected)})
    return {"version": VERSION, "rows": rows, "missing_runs": missing, "cohorts": cohorts,
            "decision": "complete_no_automatic_promotion" if not missing else "incomplete",
            "final_goal_verified": False, "large_scale_authorized": False,
            "binary_verification": "JSON only; independently verify model/RMS integrity and saved-policy replay",
            "warning": "BC adds supervised work; arms are not equal compute. Structured cases are not IID."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    make = sub.add_parser("prepare")
    make.add_argument("--directory", required=True, type=Path)
    make.add_argument("--timing-directory", required=True, type=Path)
    make.add_argument("--dataset", required=True, type=Path)
    check = sub.add_parser("summarize")
    check.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(args.directory, args.timing_directory, args.dataset)
        print("Prepared only; no training/reservation:", args.directory)
    else:
        require(args.directory.is_absolute(), "Use an absolute campaign path")
        print(json.dumps(aggregate(args.directory), indent=2))


if __name__ == "__main__":
    main()
