"""Fresh bounded physics-only worker; original saved-feedback gates stay exact."""
import json
import math
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from deploy.inference_worker import (
    REPO, SPACE, configure_http_requests, pinned_json, validate_bounded_ticket)
from deploy.space_worker import FINAL_PHASES, require_unattended_runtime
from research.campaign import digest
from research.provenance import fingerprint
from research.timing_campaign import PROVENANCE_KEYS
from tools.linux_noise_probe import BASELINE_SHA, PLAN_SHA, contract, validate_report
from tools.imitation_noise_probe import child_environment
from tools.matched_host_inference import InferenceValidationError, require, sha

VERSION = "linux-noise-probe-admission-v1"
INPUTS = {
    "model.zip": (1000930, "25ec7c319b7a9eb11c2e3b184debe12c256730af0a36d11762e75a82f7acdb87"),
    "normalization.pkl": (7385, "59bdee0d177e6724b10e84f9797c5a823e97f1ef81652ed23fb0e3c37b0e2493"),
    "remote_baselines.json": (9059490, BASELINE_SHA),
    "causal_probe_plan.json": (None, PLAN_SHA),
}


def validate_ticket(ticket, ledger, now, environment):
    return validate_bounded_ticket(
        ticket, ledger, now, environment, version=VERSION, contract_hash=digest(contract()),
        prefix="noise-probe-", mode="noise_control_probe", reservation_status="reserved_noise_probe")


def restore_inputs(worker, specs):
    from huggingface_hub import hf_hub_download
    require(set(specs) == set(INPUTS), "Unexpected frozen probe input set")
    target = worker.artifacts / "noise_probe_inputs"
    require(not target.exists(), "Fresh probe input directory required")
    target.mkdir()
    for name, (size, expected_sha) in INPUTS.items():
        spec = specs[name]
        revision, filename = spec["revision"], spec["path"]
        require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
                "Immutable owned probe input revision required")
        if name in ("model.zip", "normalization.pkl"):
            require(revision == "5df6c20390ca641d8d10a2c62471e7f4142b922e"
                    and filename == "imitation-20261004-v1/imitation_campaign/runs/"
                        "behavior_cloning_only_seed_7/" + name, "Selected clone identity changed")
        else:
            require(filename == f"{worker.session}/operator/inputs/{name}",
                    "Probe metadata must belong to the fresh session")
        require(spec["sha256"] == expected_sha and
                (spec["size"] == size if size is not None else 0 < spec["size"] <= 2 * 2**20),
                "Frozen probe input identity changed")
        metadata = worker.api.repo_info(REPO, repo_type="dataset", revision=revision, files_metadata=True)
        require(metadata.private, "Private owned probe inputs required")
        item = next((item for item in metadata.siblings if item.rfilename == filename), None)
        require(item is not None and item.size == spec["size"], "Pinned probe metadata differs")
        if item.lfs is not None:
            require(item.lfs.sha256 == expected_sha, "Pinned probe LFS metadata differs")
        source = Path(hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=filename))
        require(source.stat().st_size == spec["size"] and sha(source) == expected_sha,
                "Frozen probe bytes changed after download")
        shutil.copyfile(source, target / name)
    return target


def run_noise_probe(worker):
    worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
    require(math.isfinite(worker.deadline) and time.time() + 60 < worker.deadline <= time.time() + 1200,
            "Invalid physics-only absolute budget")
    configure_http_requests()
    threading.Thread(target=worker.watchdog, daemon=True).start()
    try:
        previous = worker.restore_status()
        if previous:
            if previous["phase"] not in FINAL_PHASES:
                worker.write_status(phase="interrupted", error="Physics-only probe interrupted; no resume")
            else:
                worker.status.update(previous)
            return
        revision = os.environ.get("RL_CONTEXT_REVISION", "")
        require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
                "Immutable fresh probe context required")
        payload = pinned_json(worker, revision, f"{worker.session}/operator/noise_probe_context.json")
        admitted = validate_ticket(payload["ticket"], payload["ledger"], time.time(), os.environ)
        require(admitted["deadline_epoch"] == worker.deadline
                and payload["ticket"]["deadline_epoch"] - payload["ticket"]["start_epoch"]
                    <= worker.max_hours * 3600, "Probe runtime cap differs")
        info = worker.api.repo_info(SPACE, repo_type="space")
        require(info.private and info.sha == payload["ticket"]["source_space_revision"],
                "Actual private probe source differs")
        current = fingerprint()
        require(all(current[key] == payload["provenance"][key] for key in PROVENANCE_KEYS),
                "Original game/source changed before probe")
        amendment = payload["transport_amendment"]
        require(amendment["version"] == contract()["version"]
                and amendment["original_plan_sha256"] == PLAN_SHA
                and amendment["scientific_plan_unchanged"] is True
                and amendment["maximum_reserved_compute_usd"] == .01
                and amendment["maximum_child_seconds"] == 600,
                "Explicit predeclared paid Linux transport amendment required")
        runtime = require_unattended_runtime(worker.api.get_space_runtime(SPACE))
        worker.write_status(phase="noise_probe_admitted", study_kind="physics_only",
                            source_space_revision=info.sha, operator_context_revision=revision,
                            campaign_budget_start_epoch=payload["ticket"]["start_epoch"],
                            deadline_epoch=worker.deadline, provenance=current, runtime_policy=runtime)
        require(worker.bounded_sync(), "Probe admission must be durable before inputs/physics")
        inputs = restore_inputs(worker, payload["inputs"])
        output = worker.artifacts / "noise_probe_result"
        claim = worker.artifacts / "noise_probe_claim.json"
        require(not claim.exists() and not output.exists(), "Existing probe execution cannot resume")
        claim.write_text(json.dumps({"state": "claimed_no_resume", "session": worker.session,
                                    "context_revision": revision, "contract": contract()}), encoding="utf-8")
        worker.write_status(phase="noise_probe_claimed", claim=json.loads(claim.read_text()),
                            claim_sha256=sha(claim))
        require(worker.bounded_sync(), "Probe claim must be durable before physics")
        def backup_progress():
            while not worker.stop.wait(20):
                if not worker.bounded_sync(timeout=10):
                    worker.stop.set();worker.terminate_owned_job()
                    worker.write_status(phase="failed", error="Probe progress backup failed")
                    worker.flush_and_pause()
                    return
        threading.Thread(target=backup_progress, daemon=True).start()
        import psutil
        work_deadline = min(time.time() + 570, worker.deadline - 90)
        require(work_deadline > time.time(), "Probe has no bounded work time left")
        grant = worker.artifacts / "noise_probe_grant.json"
        grant.write_text(json.dumps({"ticket": payload["ticket"], "ledger": payload["ledger"],
                                    "provenance": current, "parent_pid": os.getpid(),
                                    "parent_creation_time": psutil.Process().create_time(),
                                    "launcher_executable": sys.executable,
                                    "inputs_dir": str(inputs), "output_dir": str(output),
                                    "claim_file": str(claim), "claim_sha256": sha(claim),
                                    "worker_deadline_epoch": work_deadline,
                                    "wrapper_sha256": sha(Path(__file__).resolve().parents[1]
                                                         / "tools/linux_noise_probe.py"),
                                    "diagnostic_source_sha256": sha(Path(__file__).resolve().parents[1]
                                                                  / "tools/imitation_noise_probe.py")}),
                         encoding="utf-8")
        environment = {**child_environment(os.environ), "RL_NOISE_GRANT_SHA": sha(grant)}
        worker.run_command([sys.executable, "-m", "tools.linux_noise_probe", "--grant", str(grant)],
                           "noise_control_probe", environment=environment,
                           timeout_seconds=min(600, max(.1, work_deadline + 30 - time.time())))
        result = json.loads((output / "report.json").read_text(encoding="utf-8"))
        status = validate_report(result)
        worker.write_status(phase=("noise_probe_complete" if status == "completed_exploratory_diagnostic"
                                   else "noise_probe_stopped"), result_status=status,
                            result="noise_probe_result/report.json")
    except Exception as error:
        worker.write_status(phase="failed", error=(
            str(error) if isinstance(error, InferenceValidationError) else
            "Physics-only probe failed: " + type(error).__name__))
    finally:
        worker.stop.set();worker.terminate_owned_job()
        time.sleep(2.1)
        worker.flush_and_pause()
