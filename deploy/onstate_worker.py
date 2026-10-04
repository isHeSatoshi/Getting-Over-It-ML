"""Private source-pinned preflight/study worker for the logged-success comparison."""
import json
import math
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from deploy.inference_worker import configure_http_requests
from deploy.space_worker import FINAL_PHASES, require_unattended_runtime, sanitized
from research.demonstrations import require
from research.onstate_campaign import dataset_contract, prepare
from research.onstate_execution import FINALIZATION_SECONDS, PREFLIGHT_CHECKS, execute, validate_admission
from research.provenance import fingerprint


def pinned_file(worker, revision, filename, maximum):
    from huggingface_hub import hf_hub_download
    require(isinstance(revision, str) and len(revision) == 40
            and all(c in "0123456789abcdef" for c in revision), "Immutable private data revision required")
    metadata = worker.api.repo_info(worker.artifact_repo, repo_type="dataset",
                                   revision=revision, files_metadata=True)
    item = next((item for item in metadata.siblings if item.rfilename == filename), None)
    require(metadata.private and item is not None and type(item.size) is int and 0 < item.size <= maximum,
            "Pinned private data missing or exceeds byte limit")
    path = Path(hf_hub_download(worker.artifact_repo, repo_type="dataset", revision=revision, filename=filename))
    require(path.stat().st_size == item.size, "Changed pinned file size")
    return path


def pinned_context(worker):
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    path = pinned_file(worker, revision, f"{worker.session}/operator/onstate_context.json", 2 * 2**20)
    return json.loads(path.read_text(encoding="utf-8")), revision


def restore_dataset(worker, context, current):
    spec, target = context["dataset"], worker.artifacts / "training_corpus"
    require(spec["session"] == worker.session, "On-state corpus must be owned by this fresh session")
    if target.exists():
        require(worker.mode == "onstate_study"
                and dataset_contract(target, current) == context["ticket"]["dataset"],
                "Only a passed study may reuse its unchanged admitted corpus")
        return target
    target.mkdir(exist_ok=False)
    for name in ("manifest.json", "data.npz"):
        path = pinned_file(worker, spec["dataset_revision"],
                           f"{worker.session}/operator/training_corpus/{name}",
                           (8 if name.endswith(".npz") else 2) * 2**20)
        shutil.copyfile(path, target / name)
    require(dataset_contract(target, current) == context["ticket"]["dataset"],
            "Pinned on-state corpus differs from admitted data/RMS")
    return target


def preflight_commands(worker, dataset):
    base = [sys.executable, "-m"]
    commands = [
        ("unit_tests", base + ["unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]),
        ("collision_tests", ["node", "tests/collision_memo.test.js"]),
        ("fidelity", base + ["research.fast_fidelity", "--headless"]),
        ("timing_fidelity", base + ["research.timing_fidelity", "--headless", "--ticks", "384"]),
        ("benchmark", base + ["research.benchmark", "--fast"]),
        ("resources", base + ["research.resources", "--decisions", "128"]),
    ]
    from research.onstate_study import ARMS
    for name, arm in zip(PREFLIGHT_CHECKS[6:], ARMS):
        commands.append((name, base + ["research.onstate_train", "--arm", arm, "--seed", "9",
                         "--dataset", str(dataset), "--smoke", "--output-dir",
                         str(worker.artifacts / "preflight_smokes" / arm)]))
    require(tuple(name for name, _ in commands) == PREFLIGHT_CHECKS, "Changed on-state preflight checks")
    return commands


def validate_context(worker, context, current, previous):
    ticket = context["ticket"]
    if worker.mode == "onstate_preflight":
        require(previous is None and ticket["preflight"] is None,
                "Fresh on-state preflight cannot overwrite passed evidence")
        admission = {**ticket, "preflight": {
            "phase": "preflight_complete", "session": worker.session,
            "source_space_revision": ticket["source_space_revision"],
            "deadline_epoch": ticket["deadline_epoch"], "campaign_budget_start_epoch": ticket["start_epoch"],
            "provenance": current, "checks": {name: True for name in PREFLIGHT_CHECKS},
            "dataset": ticket["dataset"]}}
    else:
        require(previous is not None and previous["phase"] == "preflight_complete"
                and previous.get("study_kind") == "onstate",
                "Study requires this fresh session's passed on-state preflight")
        require(ticket["preflight"] == {key: previous[key] for key in (
            "phase", "session", "source_space_revision", "deadline_epoch", "campaign_budget_start_epoch",
            "provenance", "checks", "dataset")}, "Ticket differs from durable passed preflight")
        admission = ticket
    result = validate_admission(admission, context["ledger"], current, time.time(), os.environ)
    require(worker.deadline == result["deadline_epoch"]
            and worker.deadline - ticket["start_epoch"] <= worker.max_hours * 3600,
            "Worker absolute cap differs from admitted budget")
    actual = worker.api.repo_info(worker.space, repo_type="space")
    require(actual.private and actual.sha == ticket["source_space_revision"],
            "Actual private deployed source differs")
    return result


def backup_progress(worker):
    while not worker.stop.wait(20):
        if not worker.bounded_sync(timeout=10):
            worker.stop.set()
            worker.terminate_owned_job()
            worker.write_status(phase="failed", error="On-state durable progress backup failed")
            return


def run_onstate(worker):
    try:
        worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
        require(math.isfinite(worker.deadline)
                and time.time() + FINALIZATION_SECONDS < worker.deadline <= time.time() + 7200,
                "Invalid on-state absolute deadline")
        configure_http_requests()
        threading.Thread(target=worker.watchdog, daemon=True).start()
        previous = worker.restore_status()
        if previous and previous["phase"] not in FINAL_PHASES:
            worker.write_status(phase="interrupted", error="On-state work interrupted; no silent resume")
            return
        if previous and not (worker.mode == "onstate_study" and previous["phase"] == "preflight_complete"
                             and previous.get("study_kind") == "onstate"):
            worker.status.update(previous)
            return
        context, revision = pinned_context(worker)
        current = fingerprint()
        validate_context(worker, context, current, previous)
        runtime = require_unattended_runtime(worker.api.get_space_runtime(worker.space))
        worker.write_status(phase="onstate_admitted", study_kind="onstate", provenance=current,
                            source_space_revision=context["ticket"]["source_space_revision"],
                            operator_context_revision=revision, runtime_policy=runtime,
                            campaign_budget_start_epoch=context["ticket"]["start_epoch"],
                            deadline_epoch=worker.deadline, dataset=context["ticket"]["dataset"])
        require(worker.bounded_sync(), "On-state admission must be durable before work")
        threading.Thread(target=backup_progress, args=(worker,), daemon=True).start()
        dataset = restore_dataset(worker, context, current)
        if worker.mode == "onstate_preflight":
            checks = {}
            for name, args in preflight_commands(worker, dataset):
                worker.run_command(args, name)
                checks[name] = True
            worker.write_status(phase="preflight_complete", checks=checks)
        else:
            campaign = worker.artifacts / "onstate_campaign"
            prepare(campaign, dataset)
            worker.write_status(phase="onstate_dispatch")
            require(worker.bounded_sync(), "On-state dispatch must be durable before learners")
            execute(campaign, dataset, context["ticket"], context["ledger"],
                    dispatch=worker.run_command, durable_claim=worker.bounded_sync)
            worker.write_status(phase="onstate_complete")
    except Exception as error:
        worker.write_status(phase="failed", error=sanitized(error))
    finally:
        worker.stop.set()
        try:
            worker.terminate_owned_job()
        finally:
            time.sleep(2.1)
            worker.flush_and_pause()
