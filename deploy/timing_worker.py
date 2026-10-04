"""Owned private-context timing worker integration; no public action endpoint."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from deploy.space_worker import FINAL_PHASES, require_unattended_runtime, sanitized
from research.campaign import digest
from research.provenance import fingerprint
from research.timing_campaign import prepare, require
from research.timing_execution import FINALIZATION_SECONDS, PREFLIGHT_CHECKS, execute, validate_admission


def pinned_context(worker):
    """Fetch only JSON from this owned session at one operator-pinned dataset commit."""
    from huggingface_hub import hf_hub_download
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
            "An immutable private context dataset revision is required")
    source = hf_hub_download(worker.artifact_repo, repo_type="dataset", revision=revision,
                             filename=f"{worker.session}/operator/timing_context.json",
                             token=os.environ.get("HF_TOKEN"))
    require(Path(source).stat().st_size <= 2 * 2**20, "Operator context exceeds its bounded JSON limit")
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    return payload, revision


def preflight_commands(worker):
    base = [sys.executable, "-m"]
    commands = [
        ("unit_tests", base + ["unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]),
        ("collision_tests", ["node", "tests/collision_memo.test.js"]),
        ("fidelity", base + ["research.fast_fidelity", "--headless"]),
        ("timing_fidelity", base + ["research.timing_fidelity", "--headless", "--ticks", "384"]),
        ("benchmark", base + ["research.benchmark", "--fast"]),
        ("resources", base + ["research.resources", "--decisions", "128"]),
    ]
    for repeat in (1, 4):
        commands.append((f"timing_smoke_repeat_{repeat}", base + [
            "research.train", "--algorithm", "ppo", "--action", "absolute", "--backend", "fast",
            "--smoke", "--timing-study", "--frame-skip", str(repeat), "--steps", str(256 // repeat),
            "--seed", "3", "--output-dir", str(worker.artifacts / "preflight_smokes" / f"repeat_{repeat}")]))
    require(tuple(name for name, _ in commands) == PREFLIGHT_CHECKS, "Preflight check set changed")
    return commands


def validate_context(worker, context, current, previous):
    ticket, ledger = context["ticket"], context["ledger"]
    # A new preflight can use the same pure reservation checks with a temporary
    # local placeholder for unrun checks. It cannot be used to start learners.
    admission = ticket
    if worker.mode == "timing_preflight":
        require(previous is None, "Timing preflight cannot overwrite a persisted session")
        require(ticket["preflight"] is None, "New preflight context must not claim passed checks")
        admission = {**ticket, "preflight": {
            "phase": "preflight_complete", "session": worker.session,
            "source_space_revision": ticket["source_space_revision"],
            "deadline_epoch": ticket["deadline_epoch"],
            "campaign_budget_start_epoch": ticket["start_epoch"], "provenance": current,
            "checks": {name: True for name in PREFLIGHT_CHECKS}}}
    else:
        require(previous is not None and previous["phase"] == "preflight_complete"
                and previous.get("study_kind") == "timing",
                "Timing study requires this fresh session's complete timing preflight")
        require(ticket["preflight"] == {
            key: previous[key] for key in (
                "phase", "session", "source_space_revision", "deadline_epoch",
                "campaign_budget_start_epoch", "provenance", "checks")},
            "Operator admission differs from durable preflight evidence")
    admitted = validate_admission(admission, ledger, current, time.time(), os.environ)
    require(worker.deadline == admitted["deadline_epoch"]
            and admitted["deadline_epoch"] - ticket["start_epoch"] <= worker.max_hours * 3600,
            "Worker deadline/cap differs from reservation")
    require(worker.api.repo_info(worker.space, repo_type="space").sha == ticket["source_space_revision"],
            "Actual deployed Space revision differs from admission")
    return admitted


def restore_pilot(worker, context):
    """Bounded JSON-only import of frozen pilot evidence, never checkpoint resume."""
    from huggingface_hub import hf_hub_download
    spec = context["prior_pilot"]
    require(spec["session"] == "poc-20261004-v2" and len(spec["dataset_revision"]) == 40,
            "Expected immutable completed replacement-pilot evidence")
    prefix = spec["session"] + "/pilot_campaign/"
    target = worker.artifacts / "prior_pilot"
    target.mkdir(exist_ok=False)

    def copy_json(relative):
        path = hf_hub_download(worker.artifact_repo, repo_type="dataset", revision=spec["dataset_revision"],
                               filename=prefix + relative, token=os.environ.get("HF_TOKEN"))
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(Path(path).stat().st_size <= 32 * 2**20, "Pilot JSON import exceeds its bounded file limit")
        shutil.copyfile(path, destination)
        return json.loads(destination.read_text(encoding="utf-8"))

    campaign = copy_json("campaign.json")
    from research.campaign import plan, aggregate
    require(campaign["plan"] == plan(), "Prior pilot protocol changed")
    for run in campaign["plan"]["runs"]:
        for filename in ("manifest.json", "training_summary.json", "evaluation.json"):
            copy_json("runs/" + run["name"] + "/" + filename)
    summary = aggregate(target)
    require(digest(summary) == spec["summary_sha256"], "Pinned prior pilot summary differs")
    return target


def run_timing(worker):
    # Start the independent budget watchdog before network context/status reads.
    worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
    require(worker.deadline > time.time() + FINALIZATION_SECONDS
            and worker.deadline < time.time() + 16 * 3600, "Invalid timing worker absolute deadline")
    threading.Thread(target=worker.watchdog, daemon=True).start()
    try:
        context, revision = pinned_context(worker)
        previous = worker.restore_status()
        if previous and previous["phase"] not in FINAL_PHASES:
            worker.write_status(phase="interrupted", error="Persisted timing work interrupted; no silent restart")
            return
        if previous and not (worker.mode == "timing_study" and previous["phase"] == "preflight_complete"
                             and previous.get("study_kind") == "timing"):
            # Preserve completed/failed evidence, including a repeated preflight.
            # Only an explicit timing-study start from its matching preflight
            # may advance an existing session.
            worker.status.update(previous)
            return
        current = fingerprint()
        validate_context(worker, context, current, previous)
        runtime = require_unattended_runtime(worker.api.get_space_runtime(worker.space))
        worker.write_status(
            phase="timing_admitted", study_kind="timing", operator_context_revision=revision,
            source_space_revision=context["ticket"]["source_space_revision"],
            campaign_budget_start_epoch=context["ticket"]["start_epoch"], deadline_epoch=worker.deadline,
            provenance=current, runtime_policy=runtime)
        require(worker.bounded_sync(), "Initial timing state must be durable before any jobs")
        threading.Thread(target=worker.periodic_sync, daemon=True).start()
        if worker.mode == "timing_preflight":
            checks = {}
            for name, args in preflight_commands(worker):
                worker.run_command(args, name)
                checks[name] = True
            worker.write_status(phase="preflight_complete", checks=checks)
        else:
            pilot = restore_pilot(worker, context)
            campaign = worker.artifacts / "timing_campaign"
            prepare(campaign, pilot)
            # Mark dispatch durably before any learner; abrupt provider loss
            # must never look like an untouched successful preflight.
            worker.write_status(phase="timing_dispatch")
            require(worker.bounded_sync(), "Dispatch status must be durable before execution")
            execute(campaign, context["ticket"], context["ledger"], dispatch=worker.run_command,
                    durable_claim=worker.bounded_sync)
            worker.write_status(phase="timing_complete")
    except Exception as error:
        worker.write_status(phase="failed", error=sanitized(error))
    finally:
        worker.stop.set()
        worker.terminate_owned_job()
        time.sleep(2.1)
        worker.flush_and_pause()
