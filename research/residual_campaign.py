"""Contract validation and conservative goal projection for completed residual runs."""
import json
import hashlib
from pathlib import Path

from research.campaign import digest
from research.demonstrations import require
from research.residual_evaluation import summarize
from research.residual_study import CASES, SEEDS, TRANSITIONS, MAX_RESETS, plan
from research.residual_execution import VERSION as ADMISSION_VERSION
from research.phase_controller import SOURCE_DATA_SHA
from research.timing_campaign import PROVENANCE_KEYS
from tools.research_goal_metrics import goal_metrics


def read(path):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 128*2**20,
            "Missing/oversized residual contract JSON")
    return json.loads(path.read_text())


def write_evaluation(directory, phase, records):
    """Bounded per-case traces, not a single oversized nine-case JSON."""
    require(phase in ("baseline", "final") and len(records) == len(CASES),
            "Unknown residual evaluation phase/case count")
    directory = Path(directory)
    target = directory/f"evaluation_{phase}"
    target.mkdir(exist_ok=False)
    entries = []
    for expected, record in zip(CASES, records):
        require(record["case"]["name"] == expected.name, "Changed stored evaluation order")
        path = target/f"{expected.name}.json"
        payload = json.dumps(record, separators=(",", ":"), allow_nan=False).encode()
        require(0 < len(payload) <= 128*2**20, "Residual case trace exceeds bounded JSON limit")
        with path.open("xb") as stream:
            stream.write(payload)
        entries.append({"case": expected.name, "file": path.relative_to(directory).as_posix(),
                        "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})
    index = {"version": "residual-case-file-index-v1", "backend": "reference", "case_files": entries}
    with (directory/f"evaluation_{phase}.json").open("x") as stream:
        json.dump(index, stream, indent=2)


def load_evaluation(directory, phase):
    directory = Path(directory)
    index = read(directory/f"evaluation_{phase}.json")
    require(index["version"] == "residual-case-file-index-v1" and index["backend"] == "reference"
            and len(index["case_files"]) == 9, "Changed residual evaluation index")
    records = []
    for expected, entry in zip(CASES, index["case_files"]):
        require(entry["case"] == expected.name
                and entry["file"] == f"evaluation_{phase}/{expected.name}.json",
                "Residual case index path/order mismatch")
        path = directory/entry["file"]
        record = read(path)
        require(path.stat().st_size == entry["bytes"]
                and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"],
                "Residual case-file hash/size mismatch")
        records.append(record)
    return records


def validate_directory(directory, seed, current):
    directory = Path(directory)
    manifest, training = [read(directory/name) for name in ("manifest.json", "training_summary.json")]
    require(seed in SEEDS and manifest["version"] == "residual-trainer-v1"
            and manifest["purpose"] == "admitted remote residual PPO" and manifest["seed"] == seed
            and manifest["plan"] == training["plan"] == plan() and training["seed"] == seed,
            "Changed residual run/seed/plan or mock artifacts")
    require(all(manifest["provenance"][key] == current[key] for key in PROVENANCE_KEYS),
            "Mixed residual source/game provenance")
    admission = manifest["admission"]
    require(admission["version"] == ADMISSION_VERSION
            and admission["session"].startswith("residual-") and admission["seed"] == seed
            and type(admission["deadline_epoch"]) in (int, float) and admission["deadline_epoch"] > 0
            and len(admission["source_space_revision"]) == 40
            and admission["prior_data_sha256"] == SOURCE_DATA_SHA,
            "Missing residual execution admission")
    physical, optimizer = training["physical"], training["optimizer"]
    require(manifest["checkpoint_contract"]["schema"]["adapter"]["scaffold"]["actor_dimension"] == 222
            and manifest["checkpoint_contract"]["schema"] == plan()["policy"]
            and manifest["checkpoint_contract"]["prior"] == {
                "observations": plan()["policy"]["adapter"]["scaffold"]["base"]["nominal_pre_observations_sha256"],
                "actions": plan()["policy"]["adapter"]["scaffold"]["base"]["nominal_applied_actions_sha256"]},
            "Changed actor dimension or hash-bound source prior")
    checkpoint_sources = manifest["checkpoint_contract"]["source_sha256"]
    require(checkpoint_sources == {name: current["source_sha256"]["research/"+name] for name in
            ("residual_controller.py", "residual_env.py", "residual_policy.py", "stroke_controller.py")},
            "Residual checkpoint source hashes changed")
    require(all(type(value) is int for value in (
                training["transitions"], physical["decision_steps"], physical["controlled_physics_ticks"],
                physical["resets"], physical["reset_settling_physics_ticks"],
                optimizer["total_optimizer_step_calls"])), "Residual work counters must be integers")
    require(training["ppo"] == plan()["ppo"]
            and training["complete"] is True and training["mock_smoke"] is False
            and training["transitions"] == physical["decision_steps"] == physical["controlled_physics_ticks"] == TRANSITIONS
            and physical["frame_skip"] == 1 and 1 <= physical["resets"] <= MAX_RESETS
            and physical["reset_settling_physics_ticks"] == physical["resets"]*120
            and physical["total_counted_physics_ticks"] == TRANSITIONS+physical["resets"]*120
            and optimizer["optimizer_step_calls"] == {"policy": optimizer["total_optimizer_step_calls"]}
            and 0 < optimizer["total_optimizer_step_calls"] <= 3072
            and training["checkpoints"] == [65536, TRANSITIONS]
            and training["bootstrap_ticks"] == 240 and training["saved_reload_exact"] is True,
            "Incomplete/changed residual actual work, checkpoints or replay")
    for step in (65536, TRANSITIONS):
        checkpoint = read(directory/f"checkpoint_{step}.json")
        model, normalizer = directory/f"model_{step}.zip", directory/f"normalizer_{step}.pkl"
        require(model.is_file() and normalizer.is_file() and not model.is_symlink() and not normalizer.is_symlink()
                and 0 < model.stat().st_size <= 32*2**20 and 0 < normalizer.stat().st_size <= 2*2**20,
                "Missing/bounded residual model/RMS companions")
        require(checkpoint["transitions"] == step
                and checkpoint["contract"] == manifest["checkpoint_contract"]
                and checkpoint["admission"] == admission
                and hashlib.sha256(model.read_bytes()).hexdigest() == checkpoint["model_sha256"]
                and hashlib.sha256(normalizer.read_bytes()).hexdigest() == checkpoint["normalizer_sha256"],
                "Residual checkpoint companion hashes/source/normalizer mismatch")
    before, after = [load_evaluation(directory, phase) for phase in ("baseline", "final")]
    a, b = summarize(before, zero_actor=True), summarize(after)
    return {"seed": seed, "baseline": a, "after": b, "admission": admission,
            "baseline_sha256": digest(before),
            "dependencies": {key: manifest[key] for key in ("python", "numpy", "torch", "stable_baselines3")}}


def aggregate(directory):
    directory = Path(directory)
    record = read(directory/"residual_campaign.json")
    require(record["plan"] == plan(), "Prepared residual campaign changed")
    rows = [validate_directory(directory/"runs"/f"seed{seed}", seed, record["provenance"]) for seed in SEEDS]
    require(len({row["admission"]["session"] for row in rows}) == 1, "Mixed residual sessions")
    require(all({key: value for key, value in row["admission"].items() if key != "seed"} ==
                {key: value for key, value in rows[0]["admission"].items() if key != "seed"} for row in rows),
            "Mixed residual source/deadline/prior admissions")
    require(len({row["baseline_sha256"] for row in rows}) == 1
            and all(row["dependencies"] == rows[0]["dependencies"] for row in rows),
            "Zero-actor physical baseline or learner dependencies differ across seeds")
    benefits = []
    for row in rows:
        a, b = row["baseline"], row["after"]
        benefits.append(b["nominal_central_hold"] and b["holds"]["first_ledge_v1"] >= 8
            and b["deaths"] <= a["deaths"] and b["median_retained_gain"] >= a["median_retained_gain"]
            and (b["holds"]["first_ledge_v1"] > a["holds"]["first_ledge_v1"]
                 or b["full_completions"] > a["full_completions"]))
    projected = [{"variant": "residual_ppo", "seed": row["seed"], "after": {
        "cases": 9, "success_rate": row["after"]["hold_rates"]["first_ledge_v1"],
        "full_climb_success_rate": row["after"]["full_completion_rate"],
        "nominal_full_climb_success": row["after"]["nominal_full_completion"],
        "falls": row["after"]["deaths"], "median_retained_gain": row["after"]["median_retained_gain"]}} for row in rows]
    goal = goal_metrics({"rows": projected, "missing_runs": []},
                        {"training_seeds": list(SEEDS), "fixed": {"evaluation_cases": plan()["evaluation"]["cases"]}})
    return {"rows": rows, "replicated_first_ledge_benefit": all(benefits),
            "goal_metrics": goal, "final_goal_verified": False,
            "warning": "Baseline holds are hand-designed; even benefit is not a verified summit package."}
