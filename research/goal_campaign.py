"""Offline goal-pilot reservation/context helpers; never deploy or start paid work."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from research.campaign import digest
from research.demonstrations import require
from research.goal_execution import VERSION, CHECKS
from research.goal_study import plan
from research.phase_controller import SOURCE_DATA_SHA
from research.timing_execution import SPACE, ARTIFACT_REPO


def reserve(ledger, session, start, deadline, source_revision, rate_per_hour):
    """Return a new ledger, leaving the caller's on-disk ledger untouched."""
    require(session.startswith("goal-") and session.replace("-", "").isalnum()
            and all(row["session"] != session and row["verified_end_epoch"] is not None for row in ledger["batches"]),
            "Fresh goal session required; another batch is active or session reused")
    require(all(type(value) in (int, float) and math.isfinite(value) for value in (start, deadline, rate_per_hour))
            and 0 < deadline-start <= 36000 and 0 < rate_per_hour <= .03,
            "Invalid ten-hour/current-price reservation")
    require(len(source_revision) == 40 and all(c in "0123456789abcdef" for c in source_revision),
            "Actual immutable uploaded source revision required")
    cost = (deadline-start)/3600*rate_per_hour
    used = sum(row["estimated_elapsed_compute_cost_upper_bound"] for row in ledger["batches"])
    require(ledger["currency"] == "USD" and 0 < ledger["operating_ceiling"] <= 10
            and cost <= .30 and used+cost <= ledger["operating_ceiling"], "Goal pilot cumulative/own cost cap exceeded")
    result = deepcopy(ledger)
    result["batches"].append({"session": session, "space": SPACE, "tier": "cpu-upgrade",
        "start_epoch": start, "deadline_epoch": deadline, "rate_per_hour": rate_per_hour,
        "maximum_estimated_compute_cost": cost, "verified_end_epoch": None,
        "status": "reserved_preflight", "source_space_revision": source_revision,
        "actual_billed_cost_known": False, "study": plan()["version"]})
    return result


def context(ledger, session, prior, dataset_revision):
    batch = next(row for row in ledger["batches"] if row["session"] == session)
    prior = Path(prior)
    require(prior.is_absolute() and prior.is_dir() and batch["verified_end_epoch"] is None
            and len(dataset_revision) == 40, "Owned prior and fresh pinned reservation required")
    files = {name: hashlib.sha256((prior/name).read_bytes()).hexdigest() for name in ("manifest.json", "data.npz")}
    require(files["data.npz"] == SOURCE_DATA_SHA, "Changed historical scaffold source")
    ticket = {"version": VERSION, "session": session, "space": SPACE, "artifact_repo": ARTIFACT_REPO,
        "contract_sha256": digest(plan()), "paused_before_launch": True,
        "source_space_revision": batch["source_space_revision"], "start_epoch": batch["start_epoch"],
        "deadline_epoch": batch["deadline_epoch"], "context_revision": None,
        "runtime_policy": {"hardware": "cpu-upgrade", "sleep_policy": "never", "replicas": 1},
        "prior_data_sha256": SOURCE_DATA_SHA, "preflight": None}
    return {"plan": plan(), "ledger": deepcopy(ledger), "ticket": ticket,
            "prior": {"session": session, "dataset_revision": dataset_revision, "files": files},
            "activation": "Context only. Verify actual private source/runtime/PAUSED before preflight restart."}


def approve_training(previous_context, preflight, original_context_revision):
    require(preflight["phase"] == "preflight_complete" and preflight["study_kind"] == "goal",
            "Missing durable passed goal preflight")
    result = deepcopy(previous_context)
    result["ticket"]["preflight"] = {key: preflight[key] for key in (
        "phase", "session", "source_space_revision", "deadline_epoch", "campaign_budget_start_epoch",
        "provenance", "checks", "prior_data_sha256")}
    require(set(result["ticket"]["preflight"]["checks"]) == set(CHECKS)
            and all(value is True for value in result["ticket"]["preflight"]["checks"].values())
            and preflight["deadline_epoch"] == result["ticket"]["deadline_epoch"]
            and preflight["source_space_revision"] == result["ticket"]["source_space_revision"],
            "Failed/changed preflight cannot launch training")
    require(preflight["session"] == result["ticket"]["session"]
            and len(original_context_revision) == 40, "Preflight session/context changed")
    result["preflight_context_revision"] = original_context_revision
    result["ticket"]["context_revision"] = None  # Actual NEW pinned commit is bound by the worker.
    return result
