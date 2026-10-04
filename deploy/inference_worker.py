"""One admitted inference-only child, immutable budget, durable no-resume claim."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from deploy.space_worker import FINAL_PHASES, require_unattended_runtime
from research.campaign import digest
from research.provenance import fingerprint
from research.timing_campaign import PROVENANCE_KEYS
from tools.matched_host_inference import INPUTS, InferenceValidationError, contract, require, sha

SPACE = "isHeSatoshi/rl-over-it-poc-20261004"
REPO = "isHeSatoshi/rl-over-it-research-artifacts"
VERSION = "matched-host-inference-admission-v1"


def configure_http_requests():
    """Bound each HF request, including pause; do not expire the cleanup client."""
    import huggingface_hub as hub
    if hasattr(hub, "set_client_factory"):
        import httpx
        hub.set_client_factory(lambda: httpx.Client(
            timeout=httpx.Timeout(10, connect=5, pool=5), follow_redirects=True))
    else:
        import requests
        class BoundedSession(requests.Session):
            def send(self, request, **kwargs):
                kwargs["timeout"] = (5, 10)
                return super().send(request, **kwargs)
        hub.configure_http_backend(backend_factory=BoundedSession)


def validate_ticket(ticket, ledger, now, environment):
    require(ticket["version"] == VERSION and ticket["contract_sha256"] == digest(contract()),
            "Changed inference-only admission/contract")
    session = ticket["session"]
    require(session.startswith("inference-") and session.replace("-", "").isalnum()
            and ticket["space"] == SPACE and ticket["artifact_repo"] == REPO
            and ticket["paused_before_launch"] is True,
            "Fresh owned paused inference session required")
    require(environment.get("RL_SESSION_ID") == session and environment.get("RL_MODE") == "inference_probe"
            and environment.get("RL_SPACE_ID") == SPACE and environment.get("RL_ARTIFACT_REPO") == REPO,
            "Inference worker configuration differs")
    require(ticket["runtime_policy"] == {"hardware": "cpu-upgrade", "sleep_policy": "never", "replicas": 1},
            "Changed inference runtime policy")
    revision = ticket["source_space_revision"]
    require(isinstance(revision, str) and len(revision) == 40
            and all(c in "0123456789abcdef" for c in revision), "Invalid pinned Space source")
    selected = [row for row in ledger["batches"] if row["session"] == session]
    require(len(selected) == 1, "Unique inference reservation required")
    batch = selected[0]
    start, deadline, rate, reserved = (batch[key] for key in (
        "start_epoch", "deadline_epoch", "rate_per_hour", "maximum_estimated_compute_cost"))
    require(all(type(value) in (int, float) and math.isfinite(value)
                for value in (start, deadline, rate, reserved, now))
            and 0 < deadline - start <= 1200 and start <= now < deadline - 60
            and 0 < rate <= .03 and 0 < reserved <= .01
            and reserved >= (deadline - start) / 3600 * rate,
            "Invalid or expired inference reservation")
    require(batch["verified_end_epoch"] is None and batch["status"] == "reserved_inference"
            and batch["tier"] == "cpu-upgrade" and batch["space"] == SPACE
            and batch["source_space_revision"] == revision,
            "Closed/started or mismatched inference reservation")
    require(ticket["start_epoch"] == start and ticket["deadline_epoch"] == deadline
            and float(environment.get("RL_DEADLINE_EPOCH", "nan")) == deadline,
            "Immutable inference start/deadline changed")
    costs = []
    for other in ledger["batches"]:
        require(other["verified_end_epoch"] is not None or other["session"] == session,
                "Another paid reservation is active")
        cost = (other["maximum_estimated_compute_cost"] if other["verified_end_epoch"] is None
                else other["estimated_elapsed_compute_cost_upper_bound"])
        require(type(cost) in (int, float) and math.isfinite(cost) and cost >= 0, "Invalid ledger cost")
        costs.append(cost)
    require(ledger["currency"] == "USD" and 0 < ledger["operating_ceiling"] <= 10
            and sum(costs) <= ledger["operating_ceiling"], "Inference cumulative cost ceiling exceeded")
    return {"session": session, "deadline_epoch": deadline, "reserved_usd": reserved}


def pinned_json(worker, revision, filename):
    from huggingface_hub import hf_hub_download
    metadata = worker.api.repo_info(REPO, repo_type="dataset", revision=revision, files_metadata=True)
    require(metadata.private, "Inference context/artifacts must be private")
    item = next((item for item in metadata.siblings if item.rfilename == filename), None)
    require(item is not None and 0 < item.size <= 2 * 2**20, "Missing/oversized inference context")
    source = Path(hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=filename))
    require(source.stat().st_size == item.size, "Inference context size drift")
    return json.loads(source.read_text(encoding="utf-8"))


def context(worker):
    revision = os.environ.get("RL_CONTEXT_REVISION", "")
    require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
            "Immutable inference operator context required")
    return pinned_json(worker, revision, f"{worker.session}/operator/inference_context.json"), revision


def restore_inputs(worker, specs):
    from huggingface_hub import hf_hub_download
    require(set(specs) == set(INPUTS), "Unexpected inference input set")
    target = worker.artifacts / "inference_inputs"
    require(not target.exists(), "Inference input directory must be fresh")
    target.mkdir()
    for name, (size, expected_sha) in INPUTS.items():
        spec = specs[name]
        revision = spec["revision"]
        require(len(revision) == 40 and all(c in "0123456789abcdef" for c in revision),
                "Immutable inference input revision required")
        require(spec["size"] == size and spec["sha256"] == expected_sha,
                "Changed frozen inference input identity")
        filename = spec["path"]
        expected = (f"{worker.session}/operator/inputs/matched_inputs.npz" if name.endswith(".npz")
                    else "imitation-20261004-v1/imitation_campaign/runs/behavior_cloning_only_seed_7/" + name)
        require(filename == expected, "Inference input is not the owned declared artifact")
        if name != "matched_inputs.npz":
            require(revision == "5df6c20390ca641d8d10a2c62471e7f4142b922e", "Selected model revision changed")
        metadata = worker.api.repo_info(REPO, repo_type="dataset", revision=revision, files_metadata=True)
        require(metadata.private, "Inference binary inputs must remain private")
        item = next((item for item in metadata.siblings if item.rfilename == filename), None)
        require(item is not None and item.size == size and item.lfs is not None
                and item.lfs.sha256 == expected_sha, "Pinned input metadata differs before download")
        source = Path(hf_hub_download(REPO, repo_type="dataset", revision=revision, filename=filename))
        require(source.stat().st_size == size and sha(source) == expected_sha, "Pinned input bytes changed")
        shutil.copyfile(source, target / name)
    return target


def run_inference(worker):
    worker.deadline = float(os.environ.get("RL_DEADLINE_EPOCH", "nan"))
    require(math.isfinite(worker.deadline) and time.time() + 60 < worker.deadline <= time.time() + 1200,
            "Invalid inference absolute spending deadline")
    configure_http_requests()
    threading.Thread(target=worker.watchdog, daemon=True).start()
    try:
        previous = worker.restore_status()
        if previous:
            if previous["phase"] not in FINAL_PHASES:
                worker.write_status(phase="interrupted", error="Inference interrupted; no resume/retry")
            else:
                worker.status.update(previous)
            return
        payload, revision = context(worker)
        admitted = validate_ticket(payload["ticket"], payload["ledger"], time.time(), os.environ)
        require(admitted["deadline_epoch"] == worker.deadline
                and payload["ticket"]["deadline_epoch"] - payload["ticket"]["start_epoch"]
                    <= worker.max_hours * 3600, "Inference worker/reservation cap differs")
        require(worker.api.repo_info(SPACE, repo_type="space").private
                and worker.api.repo_info(SPACE, repo_type="space").sha
                    == payload["ticket"]["source_space_revision"], "Actual private source differs")
        current = fingerprint()
        require(all(current[key] == payload["provenance"][key] for key in PROVENANCE_KEYS),
                "Inference admitted source/game drift")
        runtime = require_unattended_runtime(worker.api.get_space_runtime(SPACE))
        worker.write_status(phase="inference_admitted", study_kind="inference_only",
                            source_space_revision=payload["ticket"]["source_space_revision"],
                            operator_context_revision=revision, deadline_epoch=worker.deadline,
                            campaign_budget_start_epoch=payload["ticket"]["start_epoch"],
                            runtime_policy=runtime, provenance=current)
        require(worker.bounded_sync(), "Inference admission must be durable")
        inputs = restore_inputs(worker, payload["inputs"])
        claim = worker.artifacts / "inference_claim.json"
        require(not claim.exists(), "An existing inference claim cannot resume")
        claim.write_text(json.dumps({"state": "claimed_no_resume", "session": worker.session,
                                    "context_revision": revision, "contract": contract()}), encoding="utf-8")
        worker.write_status(phase="inference_claimed", inference_claim=json.loads(claim.read_text()),
                            inference_claim_sha256=sha(claim))
        require(worker.bounded_sync(), "Inference claim must be durable before any child")
        def backup_progress():
            while not worker.stop.wait(20):
                if not worker.bounded_sync(timeout=10):
                    worker.stop.set()
                    worker.terminate_owned_job()
                    worker.write_status(phase="failed", error="Inference progress backup failed")
                    worker.flush_and_pause()
                    return
        threading.Thread(target=backup_progress, daemon=True).start()
        import psutil
        output = worker.artifacts / "inference_result"
        worker_deadline = min(time.time() + 120, worker.deadline - 60)
        grant = worker.artifacts / "inference_grant.json"
        grant.write_text(json.dumps({"ticket": payload["ticket"], "ledger": payload["ledger"],
                                    "provenance": current,
                                    "tool_sha256": sha(Path(__file__).resolve().parents[1]
                                                       / "tools/matched_host_inference.py"),
                                    "parent_pid": os.getpid(), "parent_creation_time": psutil.Process().create_time(),
                                    "inputs_dir": str(inputs), "output_dir": str(output),
                                    "claim_file": str(claim), "claim_sha256": sha(claim),
                                    "worker_deadline_epoch": worker_deadline}), encoding="utf-8")
        environment = {**os.environ, "RL_INFERENCE_GRANT_SHA": sha(grant)}
        worker.run_command([sys.executable, "-m", "tools.matched_host_inference",
                            "--inputs-dir", str(inputs), "--output-dir", str(output), "--grant", str(grant)],
                           "inference_probe", environment=environment,
                           timeout_seconds=max(.1, worker_deadline - time.time()))
        result = json.loads((output / "report.json").read_text(encoding="utf-8"))
        require(result["status"] == "inference_complete_no_goal_promotion"
                and result["kind"] == "remote_matched_host"
                and result["actual_inference_presentations"] == 3600
                and result["controlled_ticks"] == result["reset_ticks"] == result["training_updates"] == 0,
                "Inference child did not finish its declared diagnostic")
        worker.write_status(phase="inference_complete", result="inference_result/report.json")
    except Exception as error:
        # Do not persist URLs/headers from network exceptions or parent credentials.
        worker.write_status(phase="failed", error=(
            str(error) if isinstance(error, InferenceValidationError)
            else "Inference-only job failed: " + type(error).__name__))
    finally:
        worker.stop.set()
        worker.terminate_owned_job()
        time.sleep(2.1)  # Stable-file snapshot filter, never an operator polling loop.
        worker.flush_and_pause()
