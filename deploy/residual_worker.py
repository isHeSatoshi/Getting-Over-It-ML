"""Owned private residual preflight/study dispatcher with hash-verified backups."""
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

from deploy.inference_worker import configure_http_requests
from deploy.onstate_worker import pinned_file
from deploy.space_worker import FINAL_PHASES, require_unattended_runtime, sanitized
from research.demonstrations import require
from research.phase_controller import SOURCE_DATA_SHA, load_prior
from research.provenance import fingerprint
from research.residual_execution import (FINALIZATION_SECONDS, PREFLIGHT_CHECKS, execute,
                                         validate_admission, child_environment)
from research.residual_study import plan
from research.timing_execution import SPACE, ARTIFACT_REPO, remote_host


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned_context(worker):
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    path = pinned_file(worker, revision, f"{worker.session}/operator/residual_context.json", 2*2**20)
    return json.loads(path.read_text()), revision


def validate_context(worker, context, revision, current, previous):
    require(worker.mode in ("residual_preflight", "residual_study")
            and worker.space == SPACE and worker.artifact_repo == ARTIFACT_REPO
            and worker.session.startswith("residual-"), "Wrong owned residual worker targets/mode")
    require(context["plan"] == plan() and revision == os.environ.get("RL_CONTEXT_REVISION")
            and context["prior"]["session"] == worker.session, "Pinned residual plan/prior/context changed")
    # A context file cannot contain its own commit hash. Bind the ACTUAL pinned
    # read revision in memory, then place that value in every child grant.
    ticket = deepcopy(context["ticket"])
    require(ticket.get("context_revision") in (None, revision), "Embedded context revision differs")
    ticket["context_revision"] = revision
    if worker.mode == "residual_preflight":
        require(previous is None and ticket["preflight"] is None,
                "Fresh residual preflight cannot reuse completed/interrupted evidence")
        admission = {**ticket, "preflight": {
            "phase": "preflight_complete", "session": worker.session,
            "source_space_revision": ticket["source_space_revision"],
            "deadline_epoch": ticket["deadline_epoch"], "campaign_budget_start_epoch": ticket["start_epoch"],
            "provenance": current, "checks": {key: True for key in PREFLIGHT_CHECKS},
            "prior_data_sha256": SOURCE_DATA_SHA}}
    else:
        require(previous is not None and previous["phase"] == "preflight_complete"
                and previous.get("study_kind") == "residual", "Study needs its passed residual preflight")
        require(ticket["preflight"] == {key: previous[key] for key in (
            "phase", "session", "source_space_revision", "deadline_epoch", "campaign_budget_start_epoch",
            "provenance", "checks", "prior_data_sha256")}, "Ticket differs from durable residual preflight")
        require(context["preflight_context_revision"] == previous["operator_context_revision"],
                "Approved training context must bind original preflight context")
        admission = ticket
    environment = {**os.environ, "RL_MODE": "residual_study"}
    result = validate_admission(admission, context["ledger"], current, time.time(), environment)
    require(worker.deadline == result["deadline_epoch"] and 0 < worker.max_hours <= 2
            and worker.deadline-ticket["start_epoch"] <= worker.max_hours*3600,
            "Residual worker absolute budget changed")
    actual = worker.api.repo_info(worker.space, repo_type="space")
    require(actual.private and actual.sha == ticket["source_space_revision"],
            "Actual private residual deployed source differs")
    return ticket


def restore_prior(worker, context, current):
    spec, target = context["prior"], worker.artifacts/"residual_prior"
    require(spec["session"] == worker.session and spec["files"]["data.npz"] == SOURCE_DATA_SHA
            and set(spec["files"]) == {"data.npz", "manifest.json"}, "Changed residual prior identity")
    if target.exists():
        require(worker.mode == "residual_study", "Preflight cannot overwrite an existing prior")
    else:
        target.mkdir(exist_ok=False)
        for name in ("manifest.json", "data.npz"):
            source = pinned_file(worker, spec["dataset_revision"],
                f"{worker.session}/operator/prior/{name}", (32 if name.endswith(".npz") else 2)*2**20)
            require(sha(source) == spec["files"][name], "Pinned residual prior hash changed")
            shutil.copyfile(source, target/name)
    require(all((target/name).is_file() and not (target/name).is_symlink()
                and sha(target/name) == value for name, value in spec["files"].items()),
            "Restored residual prior files drifted")
    load_prior(target, current)
    return target


def preflight_commands(worker, prior):
    base = [sys.executable, "-m"]
    commands = [
        ("unit_tests", base+["unittest", "discover", "-s", "tests", "-p", "test_*.py"]),
        ("collision_tests", ["node", "tests/collision_memo.test.js"]),
        ("resources", base+["research.resources", "--decisions", "128"]),
        ("benchmark", base+["research.benchmark", "--fast"]),
    ]
    for name, check in (("residual_zero_fidelity", "fidelity"),
                        ("residual_pipeline", "pipeline"), ("residual_optimizer_smoke", "optimizer")):
        commands.append((name, base+["research.residual_preflight", "--check", check,
            "--prior", str(prior), "--output-dir", str(worker.artifacts/"preflight"/check)]))
    require(tuple(name for name, _ in commands) == PREFLIGHT_CHECKS, "Changed residual preflight checks")
    return commands


def durable_sync(worker, required=()):
    """Verify required CLOSED files in the uploaded immutable dataset revision."""
    paths = list(required)
    for path in paths:
        require(path.is_file() and not path.is_symlink() and path.is_relative_to(worker.artifacts),
                "Required residual backup path is not an owned regular file")
    if paths:
        delay = max(0., max(path.stat().st_mtime+2.05-time.time() for path in paths))
        require(time.time()+delay < worker.deadline-10, "Residual backup cleanup reserve reached")
        if delay:
            time.sleep(delay)  # Bounded stable-copy window, never an operator polling loop.
    require(time.time() < worker.deadline-10, "Residual upload reserve exhausted")
    if not worker.bounded_sync(timeout=min(10, max(.1, worker.deadline-10-time.time()))):
        return False
    if not paths:
        return True
    metadata = worker.api.repo_info(worker.artifact_repo, repo_type="dataset", files_metadata=True)
    require(metadata.private and isinstance(metadata.sha, str) and len(metadata.sha) == 40,
            "Residual backup repo must be private and revision-pinned")
    siblings = {item.rfilename: item for item in metadata.siblings}
    for path in paths:
        entry = siblings.get(f"{worker.session}/{path.relative_to(worker.artifacts).as_posix()}")
        require(entry is not None and entry.size == path.stat().st_size, "Required backup file missing/size drift")
        lfs = getattr(entry, "lfs", None)
        if lfs:
            digest = lfs.get("sha256") if isinstance(lfs, dict) else lfs.sha256
            require(digest == sha(path), "Required residual LFS backup hash drift")
        else:
            payload = path.read_bytes()
            digest = hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()
            require(entry.blob_id == digest, "Required residual Git backup hash drift")
    worker.residual_backup_revision = metadata.sha
    return True


def backup_progress(worker):
    while not worker.stop.wait(20):
        try:
            required = []
            for marker in (worker.artifacts/"residual_campaign").glob("runs/seed*/checkpoint_*.json"):
                if time.time()-marker.stat().st_mtime >= 2.05:
                    step = int(marker.stem.split("_")[-1])
                    required.extend((marker, marker.parent/f"model_{step}.zip",
                                     marker.parent/f"normalizer_{step}.pkl"))
            require(durable_sync(worker, required), "Residual progress backup failed")
        except Exception as error:
            worker.stop.set()
            worker.terminate_owned_job()
            worker.write_status(phase="failed", error=sanitized(error))
            worker.flush_and_pause()
            return


def run_residual(worker):
    attempted_pause = [False]
    def finish_pause(phase=None):
        attempted_pause[0] = True
        worker.stop.set()
        try:
            worker.terminate_owned_job()
            if phase is not None:
                worker.write_status(phase=phase)
            durable_sync(worker, [worker.state_path])
        finally:
            worker.pause()
        return str(worker.api.get_space_runtime(worker.space).stage) == "PAUSED"
    try:
        require(remote_host(os.environ), "Residual worker requires isolated Linux, not desktop")
        worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
        require(math.isfinite(worker.deadline) and time.time()+FINALIZATION_SECONDS < worker.deadline <= time.time()+7200,
                "Invalid residual absolute deadline")
        configure_http_requests()
        threading.Thread(target=worker.watchdog, daemon=True).start()
        previous = worker.restore_status()
        if previous and previous["phase"] not in FINAL_PHASES:
            worker.write_status(phase="interrupted", error="Residual work interrupted; no silent resume")
            return
        if previous and not (worker.mode == "residual_study" and previous["phase"] == "preflight_complete"
                             and previous.get("study_kind") == "residual"):
            worker.status.update(previous)
            return
        context, revision = pinned_context(worker)
        current = fingerprint()
        ticket = validate_context(worker, context, revision, current, previous)
        runtime = require_unattended_runtime(worker.api.get_space_runtime(worker.space))
        worker.write_status(phase="residual_admitted", study_kind="residual", provenance=current,
            source_space_revision=ticket["source_space_revision"], operator_context_revision=revision,
            campaign_budget_start_epoch=ticket["start_epoch"], deadline_epoch=worker.deadline,
            runtime_policy=runtime, prior_data_sha256=SOURCE_DATA_SHA)
        require(durable_sync(worker, [worker.state_path]), "Residual admission backup failed before work")
        threading.Thread(target=backup_progress, args=(worker,), daemon=True).start()
        prior = restore_prior(worker, context, current)
        if worker.mode == "residual_preflight":
            checks = {}
            for name, command in preflight_commands(worker, prior):
                worker.run_command(command, name, child_environment(os.environ), timeout_seconds=120)
                checks[name] = True
            worker.write_status(phase="preflight_complete", checks=checks)
        else:
            campaign = worker.artifacts/"residual_campaign"
            campaign.mkdir(exist_ok=False)
            with (campaign/"residual_campaign.json").open("x") as stream:
                json.dump({"plan": plan(), "provenance": current}, stream, indent=2)
            worker.write_status(phase="residual_dispatch")
            require(durable_sync(worker, [campaign/"residual_campaign.json"]), "Residual dispatch backup failed")
            def completed(seed):
                if seed == "summary":
                    paths = [campaign/"summary.json"]
                else:
                    paths = [path for path in (campaign/"runs"/f"seed{seed}").rglob("*")
                             if path.is_file() and path.suffix in (".json", ".zip", ".pkl")]
                require(paths, "No completed residual artifacts to back up")
                return durable_sync(worker, paths)
            def pause_result():
                phase = "residual_complete" if (campaign/"summary.json").is_file() else "failed"
                return finish_pause(phase)
            execute(campaign, prior, ticket, context["ledger"],
                durable_claim=lambda: durable_sync(worker, [campaign/"execution_claim.json"]),
                durable_run=completed, auto_pause=pause_result,
                dispatch=lambda args, seed, environment: worker.run_command(args, f"seed{seed}", environment))
    except Exception as error:
        if not attempted_pause[0]:
            worker.write_status(phase="failed", error=sanitized(error))
    finally:
        if not attempted_pause[0]:
            finish_pause()
