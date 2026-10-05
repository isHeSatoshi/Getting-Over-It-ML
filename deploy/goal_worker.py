"""Fresh owned HF goal-SAC preflight/pilot, using established backup/watchdog machinery."""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import threading
import time

import psutil

from deploy.inference_worker import configure_http_requests
from deploy.onstate_worker import pinned_file
from deploy.space_worker import FINAL_PHASES, require_unattended_runtime, sanitized, copy_artifact
from research.demonstrations import require
from research.goal_execution import (CHECKS, VERSION, validate_admission, child_environment)
from research.goal_study import plan, SEEDS
from research.phase_controller import SOURCE_DATA_SHA, load_prior
from research.provenance import fingerprint
from research.resources import effective_limits
from research.timing_execution import remote_host, SPACE, ARTIFACT_REPO


def pinned_context(worker):
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    path = pinned_file(worker, revision, f"{worker.session}/operator/goal_context.json", 2*2**20)
    return json.loads(path.read_text()), revision


def validate_context(worker, context, revision, current, previous):
    require(worker.mode in ("goal_preflight", "goal_study") and worker.space == SPACE
            and worker.artifact_repo == ARTIFACT_REPO and worker.session.startswith("goal-")
            and context["plan"] == plan() and revision == os.environ.get("RL_CONTEXT_REVISION"),
            "Goal worker target/plan/context mismatch")
    ticket = deepcopy(context["ticket"])
    require(ticket.get("context_revision") in (None, revision), "Embedded goal context differs")
    ticket["context_revision"] = revision
    if worker.mode == "goal_preflight":
        require(previous is None and ticket["preflight"] is None, "Preflight cannot reopen existing goal work")
        candidate = {**ticket, "preflight": {"phase": "preflight_complete", "session": worker.session,
            "source_space_revision": ticket["source_space_revision"], "deadline_epoch": ticket["deadline_epoch"],
            "campaign_budget_start_epoch": ticket["start_epoch"], "provenance": current,
            "checks": {name: True for name in CHECKS}, "prior_data_sha256": SOURCE_DATA_SHA}}
    else:
        require(previous is not None and previous["phase"] == "preflight_complete"
                and previous.get("study_kind") == "goal", "Goal training requires passed fresh preflight")
        require(ticket["preflight"] == {key: previous[key] for key in (
            "phase", "session", "source_space_revision", "deadline_epoch", "campaign_budget_start_epoch",
            "provenance", "checks", "prior_data_sha256")}, "Goal ticket/preflight drift")
        require(context["preflight_context_revision"] == previous["operator_context_revision"],
                "Training approval does not bind original goal preflight")
        candidate = ticket
    result = validate_admission(candidate, context["ledger"], current, time.time(),
                                {**os.environ, "RL_MODE": "goal_study"})
    require(result["deadline_epoch"] == worker.deadline and 0 < worker.max_hours <= 10
            and ticket["deadline_epoch"]-ticket["start_epoch"] <= worker.max_hours*3600,
            "Goal worker deadline/runtime cap changed")
    actual = worker.api.repo_info(worker.space, repo_type="space")
    require(actual.private and actual.sha == ticket["source_space_revision"], "Goal deployed source differs")
    return ticket


def restore_prior(worker, context, current):
    spec, target = context["prior"], worker.artifacts/"goal_prior"
    require(spec["session"] == worker.session and spec["files"]["data.npz"] == SOURCE_DATA_SHA
            and set(spec["files"]) == {"manifest.json", "data.npz"}, "Goal scaffold identity changed")
    if target.exists():
        require(worker.mode == "goal_study", "Preflight must restore a fresh scaffold")
    else:
        target.mkdir()
        for name in ("manifest.json", "data.npz"):
            source = pinned_file(worker, spec["dataset_revision"], f"{worker.session}/operator/prior/{name}",
                                 (32 if name.endswith(".npz") else 2)*2**20)
            require(hashlib.sha256(source.read_bytes()).hexdigest() == spec["files"][name], "Scaffold hash mismatch")
            shutil.copyfile(source, target/name)
    require(all((target/name).is_file() and not (target/name).is_symlink()
                and hashlib.sha256((target/name).read_bytes()).hexdigest() == value
                for name, value in spec["files"].items()), "Restored scaffold drift")
    load_prior(target, current)
    return target


def commands(worker, prior):
    base = [sys.executable, "-m"]
    return [
        ("unit_tests", base+["research.goal_checks"]),
        ("collision_tests", ["node", "tests/collision_memo.test.js"]),
        ("resources", base+["research.goal_preflight", "--check", "resources", "--prior", str(prior),
                           "--output-dir", str(worker.artifacts/"goal_preflight"/"resources")]),
        ("benchmark", base+["research.goal_preflight", "--check", "benchmark", "--prior", str(prior),
                           "--output-dir", str(worker.artifacts/"goal_preflight"/"benchmark")]),
        ("goal_pipeline", base+["research.goal_preflight", "--check", "pipeline", "--prior", str(prior),
                               "--output-dir", str(worker.artifacts/"goal_preflight"/"pipeline")]),
        ("goal_prefix_fidelity", base+["research.goal_preflight", "--check", "fidelity", "--prior", str(prior),
                                     "--output-dir", str(worker.artifacts/"goal_preflight"/"fidelity")]),
    ]


def stable_backup(worker, required=()):
    """Check closed checkpoint files actually exist in one private uploaded revision."""
    required = list(required)
    if required:
        require(all(path.is_file() and not path.is_symlink() and path.is_relative_to(worker.artifacts)
                    for path in required), "Backup path outside owned artifacts")
        delay = max(0., max(path.stat().st_mtime+2.05-time.time() for path in required))
        require(time.time()+delay+60 < worker.deadline, "No deadline reserve for closed-file backup")
        if delay:
            time.sleep(delay)
    require(worker.bounded_sync(timeout=min(60, max(.1, worker.deadline-20-time.time()))),
            "Goal durable upload failed or timed out")
    if not required:
        return True
    metadata = worker.api.repo_info(worker.artifact_repo, repo_type="dataset", files_metadata=True)
    require(metadata.private and len(metadata.sha) == 40, "Goal backup must be private/revision pinned")
    entries = {entry.rfilename: entry for entry in metadata.siblings}
    for path in required:
        entry = entries.get(f"{worker.session}/{path.relative_to(worker.artifacts).as_posix()}")
        require(entry is not None and entry.size == path.stat().st_size, "Goal backup file missing/size drift")
        lfs = getattr(entry, "lfs", None)
        if lfs:
            expected = lfs.get("sha256") if isinstance(lfs, dict) else lfs.sha256
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(2**20), b""):
                    digest.update(chunk)
            require(digest.hexdigest() == expected, "Goal LFS backup hash mismatch")
        else:
            payload = path.read_bytes()
            require(entry.blob_id == hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest(),
                    "Goal Git backup hash mismatch")
    worker.goal_backup_revision = metadata.sha
    return True


def progress(worker):
    while not worker.stop.wait(30):
        try:
            required = []
            for marker in (worker.artifacts/"goal_campaign").glob("seed*/training/checkpoint_*/manifest.json"):
                if time.time()-marker.stat().st_mtime >= 2.05:
                    manifest = json.loads(marker.read_text())
                    required.append(marker)
                    required.extend(marker.parent/name for name in manifest["files"])
            stable_backup(worker, required)
        except Exception as error:
            worker.stop.set()
            worker.terminate_owned_job()
            worker.write_status(phase="failed", error=sanitized(error))
            worker.flush_and_pause()
            return


def run_goal(worker):
    try:
        require(remote_host(os.environ), "Goal worker is isolated Linux remote-only")
        worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
        require(math.isfinite(worker.deadline) and time.time()+60 < worker.deadline <= time.time()+36000,
                "Invalid immutable goal deadline")
        configure_http_requests()
        threading.Thread(target=worker.watchdog, daemon=True).start()
        previous = worker.restore_status()
        if previous and previous["phase"] not in FINAL_PHASES:
            worker.write_status(phase="interrupted", error="Goal work interrupted; never resume")
            return
        if previous and not (worker.mode == "goal_study" and previous["phase"] == "preflight_complete"
                             and previous.get("study_kind") == "goal"):
            worker.status.update(previous)
            return
        context, revision = pinned_context(worker)
        current = fingerprint()
        ticket = validate_context(worker, context, revision, current, previous)
        runtime = require_unattended_runtime(worker.api.get_space_runtime(worker.space))
        limits = effective_limits()
        require(limits["logical_cpus"] >= 4 and limits["available_ram_bytes"] >= 12*2**30
                and psutil.disk_usage(worker.artifacts).free >= 10*2**30, "Insufficient goal pilot resources")
        worker.write_status(phase="goal_admitted", study_kind="goal", provenance=current,
            source_space_revision=ticket["source_space_revision"], operator_context_revision=revision,
            campaign_budget_start_epoch=ticket["start_epoch"], deadline_epoch=worker.deadline,
            runtime_policy=runtime, prior_data_sha256=SOURCE_DATA_SHA)
        stable_backup(worker, [worker.state_path])
        threading.Thread(target=progress, args=(worker,), daemon=True).start()
        prior = restore_prior(worker, context, current)
        if worker.mode == "goal_preflight":
            checks = {}
            for name, args in commands(worker, prior):
                worker.run_command(args, name, child_environment(os.environ), timeout_seconds=120)
                checks[name] = True
            # Conservative deterministic allocation includes raw resource/benchmark bridge work.
            fidelity = json.loads((worker.artifacts/"goal_preflight"/"fidelity"/"report.json").read_text())
            resources = json.loads((worker.artifacts/"goal_preflight"/"resources"/"report.json").read_text())
            benchmark = json.loads((worker.artifacts/"goal_preflight"/"benchmark"/"report.json").read_text())
            preflight_ticks = fidelity["physics_ticks"]+resources["physics_ticks"]+benchmark["physics_ticks_allocated"]
            worker.write_status(phase="preflight_complete", checks=checks, preflight_physics_ticks=preflight_ticks)
        else:
            from research.goal_evaluation import validate_evaluation
            campaign = worker.artifacts/"goal_campaign"
            campaign.mkdir(exist_ok=False)
            (campaign/"plan.json").write_text(json.dumps(plan(), indent=2))
            claim = campaign/"execution_claim.json"
            claim.write_text(json.dumps({"version": VERSION, "state": "claimed_no_resume",
                                         "session": worker.session, "deadline_epoch": worker.deadline}))
            stable_backup(worker, [claim, campaign/"plan.json"])
            results = []
            for seed in SEEDS:
                output, grant = campaign/f"seed{seed}", campaign/f"grant{seed}.json"
                require(not output.exists(), "No goal seed resume/rerun")
                payload = {"version": VERSION, "ticket": ticket, "ledger": context["ledger"],
                    "seed": seed, "output_dir": str(output), "prior_directory": str(prior),
                    "parent_pid": os.getpid(), "parent_creation_time": psutil.Process().create_time(),
                    "claim_file": str(claim), "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest(),
                    "preflight_physics_ticks": previous["preflight_physics_ticks"] if seed == SEEDS[0] else 0}
                grant.write_text(json.dumps(payload, indent=2))
                environment = {**child_environment(os.environ), "RL_GOAL_GRANT": str(grant)}
                worker.run_command([sys.executable, "-m", "research.goal_run", "--remote-training",
                    "--seed", str(seed), "--prior", str(prior), "--output-dir", str(output)],
                    f"goal_seed{seed}", environment)
                result = json.loads((output/"result.json").read_text())
                scored = validate_evaluation(output/"evaluation")
                require(result["pilot_gate_passed"] == scored["pilot_gate_passed"]
                        and result["seed"] == seed and result["physics"]["total"] <= 1200000,
                        "Goal seed result/physics budget mismatch")
                stable_backup(worker, [path for path in output.rglob("*") if path.is_file()
                                       and path.suffix in (".json", ".jsonl", ".zip", ".gz")])
                results.append(result)
                if not result["pilot_gate_passed"]:
                    break
            summary = {"version": "goal-pilot-summary-v1", "completed_seeds": [row["seed"] for row in results],
                       "all_three_pilot_gates_passed": len(results) == 3 and all(row["pilot_gate_passed"] for row in results),
                       "first_failed_seed_stopped_remaining": bool(results and not results[-1]["pilot_gate_passed"]),
                       "final_goal_verified": False, "results": results}
            (campaign/"summary.json").write_text(json.dumps(summary, indent=2))
            stable_backup(worker, [campaign/"summary.json"])
            worker.write_status(phase="goal_complete", completed_seeds=summary["completed_seeds"],
                                pilot_gate_passed=summary["all_three_pilot_gates_passed"])
    except Exception as error:
        worker.write_status(phase="failed", error=sanitized(error))
    finally:
        worker.stop.set()
        try:
            worker.terminate_owned_job()
        finally:
            time.sleep(2.1)
            worker.flush_and_pause()
