"""Prepare and strictly review the frozen six-run logged-success comparison."""
import argparse
import json
from pathlib import Path
import sys

from research.campaign import digest
from research.demonstrations import require
from research.onstate_data import load
from research.onstate_study import ARMS, SEEDS, VALIDATION_CASES, plan
from research.provenance import fingerprint
from research.timing_campaign import PROVENANCE_KEYS, finite, summarize_evaluation

VERSION = "onstate-campaign-v1"
DATA_SHA = "c2d0895d56706d3c0797effae5018928229866d95c22bb72c42706876f43c268"


def contract():
    study = plan()
    return json.loads(json.dumps({
        "version": VERSION, "study": study,
        "runs": [{"name": f"{arm}_seed_{seed}", "arm": arm, "seed": seed}
                 for seed in SEEDS for arm in ARMS],
    }))


def dataset_contract(directory, current=None):
    data = load(directory, current)
    require(data.record["data_sha256"] == DATA_SHA, "Changed reviewed on-state archive identity")
    return {"data_sha256": DATA_SHA, "rows": data.record["rows"],
            "normalization": data.record["normalization"],
            "source_files": data.record["source_files"], "array_hashes": data.record["array_hashes"]}


def prepare(directory, dataset):
    directory = Path(directory)
    require(directory.is_absolute() and not directory.exists(), "Use a fresh absolute campaign directory")
    current = fingerprint()
    record = {"contract": contract(), "provenance": current, "dataset": dataset_contract(dataset, current)}
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "onstate_campaign.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def command(run, output, dataset, smoke=False):
    output, dataset = Path(output), Path(dataset)
    require(run in contract()["runs"] and type(smoke) is bool
            and output.is_absolute() and not output.exists() and dataset.is_absolute(),
            "Use declared run, trusted data and fresh absolute output")
    return [sys.executable, "-m", "research.onstate_train", "--arm", run["arm"],
            "--seed", str(run["seed"]), "--dataset", str(dataset), "--output-dir", str(output),
            "--smoke" if smoke else "--remote-training"]


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_run(manifest, training, evaluation, run, campaign):
    require(run in contract()["runs"] and campaign["contract"] == contract(), "Changed declared campaign")
    expected_settings = {
        "architecture": [256, 256], "updates": 2000, "batch_size": 256, "learning_rate": .001,
        "gamma": plan()["reward_contract"]["gamma"], "gae_lambda": .95**.25,
        "n_steps": 128, "ppo_batch_size": 64, "n_epochs": 1,
    }
    require(manifest["version"] == "onstate-trainer-v1"
            and manifest["purpose"] == "admitted remote on-state comparison"
            and manifest["config"] == {"arm": run["arm"], "seed": run["seed"],
                                       "smoke": False, "remote_training": True}
            and manifest["settings"] == training["settings"] == expected_settings,
            "Smoke, changed initialization or wrong declared training work")
    for key in PROVENANCE_KEYS:
        require(manifest[key] == campaign["provenance"][key], "Mixed source/game: " + key)
    require(manifest["dataset"] == campaign["dataset"]
            and manifest["device"] == "cpu" and manifest["reward_normalization"] == {
                "enabled": False, "clipping": "disabled", "units": "raw_task_units"}
            and manifest["reward_contract"] == plan()["reward_contract"]
            and manifest["environment_contract"] == plan()["environment"]
            and manifest["evaluation_contract"] == contract()["study"]["evaluation"],
            "Changed data/RMS, physical environment, reward or fresh reference contract")
    admission = manifest["onstate_admission"]
    require(admission["version"] == "onstate-execution-admission-v1"
            and isinstance(admission["session"], str) and admission["session"].startswith("onstate-")
            and admission["run"] == run["name"] and finite(admission["deadline_epoch"])
            and admission["deadline_epoch"] > 0 and admission["dataset_sha256"] == DATA_SHA
            and isinstance(admission["source_space_revision"], str)
            and len(admission["source_space_revision"]) == 40
            and all(c in "0123456789abcdef" for c in admission["source_space_revision"]),
            "Missing or changed fresh source/data execution admission")
    require(training["complete"] is True and training["normalization_unchanged"] is True
            and training["nonactor_parameters_unchanged"] is True
            and training["saved_reload_exact"] is True
            and type(training["torch_threads"]) is int and training["torch_threads"] == 1,
            "Incomplete training or changed RMS/value/logstd/saved replay")
    require(all(type(training[key]) is int and training[key] == 0 for key in (
        "rl_transitions", "ppo_optimizer_calls", "training_control_ticks", "training_reset_ticks")),
        "Actor-only comparison contains undeclared PPO or physical training work")
    clone = training["cloning"]
    new = 0 if run["arm"] == ARMS[0] else 128000
    count = 3576 if run["arm"] == ARMS[0] else 5376
    require(clone["version"] == "ppo-actor-demonstration-warm-start-v1"
            and clone["purpose"] == "Admitted remote actor demonstration warm start"
            and all(type(clone[key]) is int for key in (
                "samples", "optimizer_step_calls", "batch_size", "sample_presentations", "seed", "rl_transitions"))
            and (clone["samples"], clone["optimizer_step_calls"], clone["batch_size"],
                 clone["sample_presentations"], clone["seed"], clone["rl_transitions"])
                == (count, 2000, 256, 512000, run["seed"], 0)
            and clone["learning_rate"] == .001 and clone["ppo_optimizer_state_preserved"] is True
            and all(type(clone["onstate_sampling"][key]) is int for key in (
                "original_presentations", "logged_success_presentations"))
            and clone["onstate_sampling"] == {
                "arm": run["arm"], "original_presentations": 512000-new,
                "logged_success_presentations": new, "data_sha256": DATA_SHA}
            and all(finite(clone[key]) and clone[key] >= 0 for key in (
                "mean_squared_action_error_before", "mean_squared_action_error_after", "wall_seconds")),
            "Changed actual source mixture or optimizer/sample work")
    for key in ("initial_parameters_sha256", "final_parameters_sha256"):
        require(valid_hash(training[key]), "Missing parameter identity")
    require(training["initial_parameters_sha256"] == manifest["initial_parameters_sha256"],
            "Changed matched initialization")
    versions = {key: manifest[key] for key in ("python", "numpy", "torch", "stable_baselines3")}
    require(all(isinstance(value, str) and value for value in versions.values()), "Missing dependency versions")
    require(evaluation["evaluation_backend"] == "reference"
            and evaluation["checkpoints"] == ["untrained", "after_cloning"],
            "Wrong evaluation backend/checkpoints")
    before = summarize_evaluation(evaluation["untrained"], 1, 1800, cases=VALIDATION_CASES)
    after = summarize_evaluation(evaluation["after_cloning"], 1, 1800, cases=VALIDATION_CASES)
    nominal = next(row for row in evaluation["after_cloning"] if row["case"]["name"] == "nominal")
    return {"run": run["name"], "arm": run["arm"], "seed": run["seed"], "before": before, "after": after,
            "nominal_central_hold": nominal["final"]["milestone_success"]["first_ledge_v1"],
            "initial_parameters_sha256": training["initial_parameters_sha256"],
            "untrained_trace_sha256": digest(evaluation["untrained"]),
            "cloning_work": clone, "dependencies": versions,
            "admission": {key: value for key, value in admission.items() if key != "run"}}


def read_json(path, maximum):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= maximum,
            "Missing or oversized bounded result JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(directory):
    directory = Path(directory)
    require(directory.is_absolute(), "Use an absolute trusted campaign directory")
    campaign = read_json(directory / "onstate_campaign.json", 2 * 2**20)
    require(campaign["contract"] == contract(), "Prepared on-state study changed")
    rows, missing, dependencies, admission = [], [], None, None
    for run in contract()["runs"]:
        output = directory / "runs" / run["name"]
        names = ("manifest.json", "training_summary.json", "evaluation.json")
        if any(not (output / name).is_file() for name in names):
            missing.append(run["name"])
            continue
        row = validate_run(*(read_json(output / name, (128 if name == "evaluation.json" else 2) * 2**20)
                             for name in names), run, campaign)
        if dependencies is None:
            dependencies, admission = row["dependencies"], row["admission"]
        require(row["dependencies"] == dependencies and row["admission"] == admission,
                "Mixed dependencies, sources or admitted sessions")
        if "execution_admission" in campaign:
            require(row["admission"] == campaign["execution_admission"], "Changed claimed admission")
        rows.append(row)
    for seed in SEEDS:
        selected = [row for row in rows if row["seed"] == seed]
        require(len({row["initial_parameters_sha256"] for row in selected}) <= 1
                and len({row["untrained_trace_sha256"] for row in selected}) <= 1,
                "Matched-seed initialization or untrained reference behavior differs")
    cohorts = []
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        complete = len(selected) == 3 and {row["seed"] for row in selected} == set(SEEDS)
        cohorts.append({"arm": arm, "complete": complete,
                        "worst_seed_full_completion_rate": min(
                            row["after"]["full_completion_rate"] for row in selected) if complete else None,
                        "worst_seed_central_hold_rate": min(
                            row["after"]["hold_rates"]["first_ledge_v1"] for row in selected) if complete else None,
                        "first_skill_candidate": complete and all(row["nominal_central_hold"]
                            and row["after"]["hold_rates"]["first_ledge_v1"] >= 8/9 for row in selected)})
    return {"version": VERSION, "rows": rows, "missing_runs": missing, "cohorts": cohorts,
            "final_goal_verified": False, "large_scale_authorized": False}


def goal_projection(summary):
    from tools.research_goal_metrics import goal_metrics
    rows = [{"variant": row["arm"], "seed": row["seed"], "after": {
        "cases": row["after"]["cases"], "success_rate": row["after"]["hold_rates"]["first_ledge_v1"],
        "full_climb_success_rate": row["after"]["full_completion_rate"],
        "nominal_full_climb_success": row["after"]["nominal_full_completion"],
        "falls": row["after"]["deaths"], "median_retained_gain": row["after"]["median_retained_gain"]}}
        for row in summary["rows"]]
    return goal_metrics({"rows": rows, "missing_runs": summary["missing_runs"]},
                        {"training_seeds": list(SEEDS), "fixed": {"evaluation_cases":
                            [case.describe() for case in VALIDATION_CASES]}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    summary = aggregate(args.directory)
    print(json.dumps({"summary": summary, "goal_metrics": goal_projection(summary)}, indent=2))


if __name__ == "__main__":
    main()
