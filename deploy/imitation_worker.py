"""Private, source-pinned imitation preflight/study worker and data transport."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from deploy.space_worker import FINAL_PHASES, require_unattended_runtime, sanitized
from research.campaign import digest
from research.demonstrations import require
from research.imitation_campaign import dataset_contract, prepare
from research.imitation_execution import FINALIZATION_SECONDS, PREFLIGHT_CHECKS, execute, validate_admission
from research.provenance import fingerprint


def pinned_file(worker, revision, filename, maximum_bytes):
    from huggingface_hub import hf_hub_download
    require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
            "An immutable owned dataset revision is required")
    metadata = worker.api.repo_info(worker.artifact_repo, repo_type="dataset",
                                    revision=revision, files_metadata=True)
    item = next((item for item in metadata.siblings if item.rfilename == filename), None)
    require(item is not None and type(item.size) is int and 0 < item.size <= maximum_bytes,
            "Pinned artifact missing or exceeds its byte limit")
    path = Path(hf_hub_download(worker.artifact_repo, repo_type="dataset", revision=revision,
                                filename=filename, token=os.environ.get("HF_TOKEN")))
    require(path.stat().st_size == item.size, "Pinned artifact size changed")
    return path


def pinned_context(worker):
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    path = pinned_file(worker, revision, f"{worker.session}/operator/imitation_context.json", 2 * 2**20)
    return json.loads(path.read_text(encoding="utf-8")), revision


def restore_dataset(worker, context, current):
    spec = context["dataset"]
    require(spec["session"] == worker.session, "Training corpus must be owned by this fresh session")
    target = worker.artifacts / "training_corpus"
    if target.exists():
        require(worker.mode == "imitation_study"
                and dataset_contract(target, current) == context["ticket"]["dataset"],
                "Only passed-study admission may reuse the same verified immutable corpus")
        return target
    target.mkdir(exist_ok=False)
    for filename in ("manifest.json", "data.npz"):
        source = pinned_file(worker, spec["dataset_revision"],
                             f"{worker.session}/operator/training_corpus/{filename}",
                             (32 if filename.endswith(".npz") else 2) * 2**20)
        shutil.copyfile(source, target / filename)
    require(dataset_contract(target, current) == context["ticket"]["dataset"],
            "Pinned corpus differs from the admitted training data/RMS")
    return target


def restore_timing(worker, context):
    spec = context["prior_timing"]
    require(spec["session"] == "timing-20261004-v1", "Expected the closed source-pinned timing study")
    target = worker.artifacts / "prior_timing";target.mkdir(exist_ok=False)
    from research.timing_campaign import aggregate, contract
    for relative in ["timing_campaign.json"] + [
        f"runs/{run['name']}/{filename}" for run in contract()["runs"]
        for filename in ("manifest.json", "training_summary.json", "evaluation.json")]:
        source = pinned_file(worker, spec["dataset_revision"],
                             f"{spec['session']}/timing_campaign/{relative}",
                             (128 if relative.endswith("evaluation.json") else 2) * 2**20)
        destination = target / relative;destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    result = aggregate(target)
    require(not result["missing_runs"] and digest(result) == spec["summary_sha256"],
            "Prior timing evidence differs from its reviewed pinned summary")
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
    for name, arm in zip(PREFLIGHT_CHECKS[6:], (
            "ppo_from_scratch", "behavior_cloning_only", "behavior_cloning_then_ppo")):
        commands.append((name, base + ["research.imitation_train", "--arm", arm, "--dataset", str(dataset),
                         "--seed", "6", "--smoke", "--output-dir",
                         str(worker.artifacts / "preflight_smokes" / arm)]))
    require(tuple(name for name, _ in commands) == PREFLIGHT_CHECKS, "Imitation preflight set changed")
    return commands


def validate_context(worker, context, current, previous):
    ticket, ledger = context["ticket"], context["ledger"]
    if worker.mode == "imitation_preflight":
        require(previous is None and ticket["preflight"] is None,
                "Fresh imitation preflight cannot overwrite or claim existing passed evidence")
        admission = {**ticket, "preflight": {
            "phase": "preflight_complete", "session": worker.session,
            "source_space_revision": ticket["source_space_revision"],
            "deadline_epoch": ticket["deadline_epoch"], "campaign_budget_start_epoch": ticket["start_epoch"],
            "provenance": current, "checks": {name: True for name in PREFLIGHT_CHECKS},
            "dataset": ticket["dataset"]}}
    else:
        require(previous is not None and previous["phase"] == "preflight_complete"
                and previous.get("study_kind") == "imitation",
                "Study requires this session's passed imitation preflight")
        require(ticket["preflight"] == {key: previous[key] for key in (
            "phase", "session", "source_space_revision", "deadline_epoch",
            "campaign_budget_start_epoch", "provenance", "checks", "dataset")},
            "Operator ticket differs from durable imitation preflight")
        admission = ticket
    admitted = validate_admission(admission, ledger, current, time.time(), os.environ)
    require(worker.deadline == admitted["deadline_epoch"]
            and worker.deadline - ticket["start_epoch"] <= worker.max_hours * 3600,
            "Worker budget differs from its reservation")
    require(worker.api.repo_info(worker.space, repo_type="space").sha == ticket["source_space_revision"],
            "Actual deployed source differs from imitation admission")
    return admitted


def run_imitation(worker):
    worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
    require(time.time() + FINALIZATION_SECONDS < worker.deadline <= time.time() + 16 * 3600,
            "Invalid imitation absolute budget")
    threading.Thread(target=worker.watchdog, daemon=True).start()
    try:
        context, revision = pinned_context(worker);previous = worker.restore_status()
        if previous and previous["phase"] not in FINAL_PHASES:
            worker.write_status(phase="interrupted", error="Imitation work interrupted; no silent restart")
            return
        if previous and not (worker.mode == "imitation_study" and previous["phase"] == "preflight_complete"
                             and previous.get("study_kind") == "imitation"):
            worker.status.update(previous)
            return
        current = fingerprint()
        validate_context(worker, context, current, previous)
        runtime = require_unattended_runtime(worker.api.get_space_runtime(worker.space))
        worker.write_status(phase="imitation_admitted", study_kind="imitation",
                           operator_context_revision=revision, source_space_revision=context["ticket"]["source_space_revision"],
                           campaign_budget_start_epoch=context["ticket"]["start_epoch"],
                           deadline_epoch=worker.deadline, provenance=current, runtime_policy=runtime,
                           dataset=context["ticket"]["dataset"])
        require(worker.bounded_sync(), "Admission status must be durable before imitation jobs")
        threading.Thread(target=worker.periodic_sync, daemon=True).start()
        dataset = restore_dataset(worker, context, current)
        if worker.mode == "imitation_preflight":
            checks = {}
            for name, args in preflight_commands(worker, dataset):
                worker.run_command(args, name);checks[name] = True
            worker.write_status(phase="preflight_complete", checks=checks)
        else:
            prior = restore_timing(worker, context)
            campaign = worker.artifacts / "imitation_campaign"
            prepare(campaign, prior, dataset)
            worker.write_status(phase="imitation_dispatch")
            require(worker.bounded_sync(), "Imitation dispatch must be durable before learners")
            execute(campaign, dataset, context["ticket"], context["ledger"],
                    dispatch=worker.run_command, durable_claim=worker.bounded_sync)
            worker.write_status(phase="imitation_complete")
    except Exception as error:
        worker.write_status(phase="failed", error=sanitized(error))
    finally:
        worker.stop.set();worker.terminate_owned_job()
        time.sleep(2.1);worker.flush_and_pause()
