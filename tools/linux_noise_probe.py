"""Admitted Linux transport for the immutable exploratory control protocol."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time

from tools.imitation_noise_probe import (
    digest_file, read_json, require, require_owned_parent, validate_plan, worker)

PLAN_SHA = "aeb940ac3fb32209de78795cb83ebbabc69166c28ff85c47ba10651e92fe3d7c"
BASELINE_SHA = "e1a826fb9ae3968706f090d6506032d58b23b7df65adb111715df7257f967002"


def contract():
    return {"version": "linux-noise-probe-transport-v1", "scientific_plan_sha256": PLAN_SHA,
            "remote_baselines_sha256": BASELINE_SHA,
            "controller": "Owned seed7 clone-only model and matching saved frozen RMS",
            "conditions": ["nominal", "full_noise_8105", "early_noise_8105", "late_noise_8105"],
            "maximum_child_seconds": 600, "maximum_controlled_ticks": 14400,
            "maximum_reset_ticks": 1920, "maximum_rollouts": 8, "training_updates": 0,
            "baseline_gate": "Exact original saved-feedback and reference/fast gate before interventions",
            "transport_amendment": "Fresh private Linux paid execution envelope only; original local plan immutable",
            "goal_promotion": False}


def validate_report(result):
    require(result["version"] == "causal-noise-prefix-suffix-probe-v1"
            and result["plan_sha256"] == PLAN_SHA and result["training_updates"] == 0
            and 0 <= result["case_rollouts"] <= 8
            and 0 <= result["controlled_ticks"] <= 14400
            and 0 <= result["reset_ticks"] <= 1920, "Changed diagnostic result/work budget")
    require(result["status"] in ("completed_exploratory_diagnostic",
                                "baseline_fidelity_or_portability_failed",
                                "intervention_backend_fidelity_failed"), "Incomplete probe result")
    require({"nominal", "full_noise_8105"} <= set(result["remote_differences"])
            and {"nominal", "full_noise_8105"} <= set(result["backend_differences"]),
            "Missing saved-feedback baseline comparison results")
    entries = [entry for backends in result["rollouts"].values() for entry in backends.values()]
    require(all(type(entry.get("control_ticks")) is int and 1 <= entry["control_ticks"] <= 1800
                and type(entry.get("reset_ticks")) is int and 120 <= entry["reset_ticks"] <= 240
                for entry in entries)
            and len(entries) == result["case_rollouts"]
            and sum(entry["control_ticks"] for entry in entries) == result["controlled_ticks"]
            and sum(entry["reset_ticks"] for entry in entries) == result["reset_ticks"],
            "Probe per-case physical work differs from totals")
    baseline_failed = (any(result["backend_differences"].get(key) for key in ("nominal", "full_noise_8105"))
                       or any(result["remote_differences"].get(key) for key in ("nominal", "full_noise_8105")))
    interventions = set(result["rollouts"]) & {"early_noise_8105", "late_noise_8105"}
    require(not baseline_failed or not interventions, "Interventions bypassed frozen failed baseline gate")
    if result["status"] == "completed_exploratory_diagnostic":
        require(set(result["rollouts"]) == set(contract()["conditions"]) and not baseline_failed
                and set(result["backend_differences"]) == set(contract()["conditions"])
                and not any(result["backend_differences"].values())
                and result["case_rollouts"] == 8, "Complete probe lacks exact declared cases")
        require(all(set(backends) == {"reference", "fast"} for backends in result["rollouts"].values()),
                "Complete probe lacks both declared backends")
    return result["status"]


def execute(grant_path):
    from deploy.noise_probe_worker import validate_ticket
    from research.provenance import fingerprint
    from research.timing_campaign import PROVENANCE_KEYS
    import torch
    import numpy as np
    import stable_baselines3
    grant_path = Path(grant_path)
    require(grant_path.is_absolute() and not grant_path.is_symlink()
            and grant_path.stat().st_size <= 2 * 2**20, "Invalid owned Linux probe grant")
    grant = read_json(grant_path)
    require(sys.platform == "linux" and not any(os.environ.get(key) for key in (
        "FACTORY_DESKTOP_CDP_PORT", "AGENT_BROWSER_CDP", "AGENT_BROWSER_SESSION")),
            "Physics-only transport requires isolated Linux, never desktop/browser attachment")
    require_owned_parent(grant)
    require(digest_file(grant_path) == os.environ.get("RL_NOISE_GRANT_SHA")
            and digest_file(Path(__file__).resolve()) == grant["wrapper_sha256"],
            "Linux probe grant/wrapper changed")
    validate_ticket(grant["ticket"], grant["ledger"], time.time(), os.environ)
    claim = Path(grant["claim_file"])
    output, inputs = Path(grant["output_dir"]), Path(grant["inputs_dir"])
    require(output.is_absolute() and inputs.is_absolute() and not output.exists()
            and not inputs.is_symlink() and not output.is_symlink()
            and claim.is_absolute() and claim.parent == output.parent
            and digest_file(claim) == grant["claim_sha256"], "Linux probe paths/claim changed")
    require(platform.python_version() == "3.11.17" and torch.__version__ == "2.6.0+cpu"
            and np.__version__ == "2.4.3" and stable_baselines3.__version__ == "2.7.1",
            "Matching Linux inference dependencies required before browsers")
    current = fingerprint()
    require(all(current[key] == grant["provenance"][key] for key in PROVENANCE_KEYS),
            "Linux probe original source/game drift")
    plan_path = inputs / "causal_probe_plan.json"
    require(digest_file(plan_path) == PLAN_SHA
            and digest_file(inputs / "remote_baselines.json") == BASELINE_SHA,
            "Frozen plan/baseline bytes changed")
    validate_plan(read_json(plan_path))
    core = Path(__file__).resolve().with_name("imitation_noise_probe.py")
    require(digest_file(core) == grant["diagnostic_source_sha256"], "Original probe implementation changed")
    cutoff = grant["worker_deadline_epoch"]
    require(time.time() < cutoff <= min(grant["ticket"]["deadline_epoch"] - 60, time.time() + 570),
            "600second child must preserve30seconds cleanup inside session reserve")
    output.mkdir()
    for name in ("model.zip", "normalization.pkl", "remote_baselines.json"):
        shutil.copyfile(inputs / name, output / name)
    # The original core sees the original owning parent, not this wrapper.
    prepared = {**grant, "output": str(output), "plan": str(plan_path),
                "plan_sha256": PLAN_SHA, "deadline_epoch": cutoff,
                "diagnostic_source_sha256": grant["diagnostic_source_sha256"]}
    prepared_path = output / "prepared.json"
    prepared_path.write_text(json.dumps(prepared, indent=2), encoding="utf-8")
    result = worker(prepared_path, output)
    validate_report(result)
    result["transport"] = {"version": contract()["version"], "session": grant["ticket"]["session"],
                           "source_space_revision": grant["ticket"]["source_space_revision"],
                           "start_epoch": grant["ticket"]["start_epoch"],
                           "deadline_epoch": grant["ticket"]["deadline_epoch"],
                           "child_work_deadline_epoch": cutoff,
                           "wrapper_sha256": grant["wrapper_sha256"],
                           "claim_sha256": grant["claim_sha256"],
                           "scientific_plan_unchanged": True, "transport_amendment_predeclared": True}
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grant", required=True, type=Path)
    result = execute(parser.parse_args().grant)
    print(result["status"], flush=True)
