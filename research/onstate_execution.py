"""Fresh Linux-only data-bound on-state grants, no silent resume or budget renewal."""
import hashlib
import json
import os
from pathlib import Path
import time

import psutil

from research.campaign import digest
from research.demonstrations import require
from research.onstate_campaign import (
    DATA_SHA, aggregate, command, contract, dataset_contract, goal_projection)
from research.provenance import fingerprint
from research.resources import effective_limits
from research.timing_campaign import PROVENANCE_KEYS, finite
from research.timing_execution import (
    SPACE, ARTIFACT_REPO, FINALIZATION_SECONDS, remote_host, run_bounded, validate_study_admission)

ADMISSION_VERSION = "onstate-execution-admission-v1"
PREFLIGHT_CHECKS = ("unit_tests", "collision_tests", "fidelity", "timing_fidelity", "benchmark", "resources",
                    "onstate_smoke_original", "onstate_smoke_augmented")
_PERMIT_TOKEN = object()


def validate_admission(ticket, ledger, current, now, environment):
    admitted = validate_study_admission(
        ticket, ledger, current, now, environment, version=ADMISSION_VERSION, prefix="onstate-",
        study_contract=contract(), preflight_checks=PREFLIGHT_CHECKS)
    require(environment.get("RL_MODE") in ("onstate_preflight", "onstate_study"),
            "Wrong on-state execution mode")
    batch = next(row for row in ledger["batches"] if row["session"] == ticket["session"])
    require(ticket["deadline_epoch"] - ticket["start_epoch"] <= 7200
            and finite(batch["maximum_estimated_compute_cost"])
            and batch["maximum_estimated_compute_cost"] <= .06
            and now < ticket["deadline_epoch"] - FINALIZATION_SECONDS,
            "On-state reservation exceeds its two-hour/0.06USD envelope or cleanup reserve")
    require(ticket["dataset"] == ticket["preflight"]["dataset"]
            and ticket["dataset"]["data_sha256"] == DATA_SHA,
            "Fresh preflight must bind the reviewed exact learner-state archive")
    return admitted


def child_environment(environment):
    from research.timing_execution import child_environment as without_credentials
    return {key: value for key, value in without_credentials(environment).items()
            if not any(word in key.upper() for word in ("BROWSER", "CDP", "DISPLAY"))}


class RunPermit:
    def __init__(self, payload, environment, token=None):
        require(token is _PERMIT_TOKEN, "Only the validated on-state grant loader creates permits")
        self.payload, self.environment, self.run = payload, environment, payload["run"]

    def verify(self, arm, seed, dataset_sha256=None):
        require(remote_host(self.environment) and self.environment.get("RL_MODE") == "onstate_study"
                and os.getppid() == self.payload["parent_pid"]
                and psutil.Process(os.getppid()).create_time() == self.payload["parent_creation_time"],
                "Full on-state work requires its exact live isolated Linux parent")
        require(arm == self.run["arm"] and seed == self.run["seed"],
                "Stage differs from the admitted arm/seed")
        require(time.time() < self.payload["ticket"]["deadline_epoch"] - FINALIZATION_SECONDS,
                "On-state cleanup reserve reached")
        claim = Path(self.payload["claim_file"])
        require(claim.is_file() and not claim.is_symlink()
                and hashlib.sha256(claim.read_bytes()).hexdigest() == self.payload["claim_sha256"],
                "On-state interruption claim changed")
        archive = Path(self.payload["dataset_dir"]) / "data.npz"
        require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= 8 * 2**20
                and hashlib.sha256(archive.read_bytes()).hexdigest() == DATA_SHA,
                "On-state archive changed after admission")
        require(dataset_sha256 is None or dataset_sha256 == DATA_SHA, "Wrong on-state dataset")

    def record(self):
        ticket = self.payload["ticket"]
        return {"version": ADMISSION_VERSION, "session": ticket["session"],
                "source_space_revision": ticket["source_space_revision"],
                "deadline_epoch": ticket["deadline_epoch"], "run": self.run["name"],
                "dataset_sha256": DATA_SHA}


def load_trainer_grant(args, environment=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment) and environment.get("RL_MODE") == "onstate_study",
            "Full on-state training is isolated Linux remote-only")
    filename = environment.get("RL_ONSTATE_GRANT", "")
    path = Path(filename)
    require(filename and path.is_absolute() and not path.is_symlink()
            and path.stat().st_size <= 2 * 2**20, "Missing bounded direct-parent on-state grant")
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(payload["version"] == ADMISSION_VERSION and payload["parent_pid"] == os.getppid(),
            "Wrong on-state grant parent/version")
    validate_admission(payload["ticket"], payload["ledger"], fingerprint(), time.time(), environment)
    run = payload["run"]
    require(run in contract()["runs"] and args.arm == run["arm"] and args.seed == run["seed"]
            and args.remote_training and not args.smoke, "Arguments differ from admitted on-state run")
    output, dataset = Path(args.output_dir), Path(args.dataset)
    require(output.is_absolute() and output == Path(payload["output_dir"]) and not output.exists()
            and dataset.is_absolute() and dataset == Path(payload["dataset_dir"]),
            "Changed fresh output/data paths")
    claim = Path(payload["claim_file"])
    require(claim.is_absolute() and claim.parent == output.parent.parent, "Wrong on-state claim location")
    permit = RunPermit(payload, environment, _PERMIT_TOKEN)
    permit.verify(args.arm, args.seed)
    return permit


def require_permit(permit, arm, seed, dataset_sha256=None):
    require(type(permit) is RunPermit, "Full on-state stages need a validated parent permit")
    permit.verify(arm, seed, dataset_sha256)


def execute(directory, dataset, ticket, ledger, environment=None, dispatch=None, durable_claim=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment) and environment.get("RL_MODE") == "onstate_study",
            "On-state execution is Linux remote-only")
    directory, dataset = Path(directory), Path(dataset)
    require(directory.is_absolute() and dataset.is_absolute(), "Use absolute owned campaign/data paths")
    current = fingerprint()
    admitted = validate_admission(ticket, ledger, current, time.time(), environment)
    record = json.loads((directory / "onstate_campaign.json").read_text(encoding="utf-8"))
    require(record["contract"] == contract()
            and record["dataset"] == ticket["dataset"] == dataset_contract(dataset, current),
            "Prepared/admitted/actual on-state data or protocol differs")
    require(all(record["provenance"][key] == current[key] for key in PROVENANCE_KEYS),
            "Prepared source/game drift")
    runs, claim = directory / "runs", directory / "execution_claim.json"
    require(not runs.exists() and not claim.exists(), "Existing on-state work cannot silently resume")
    limits = effective_limits()
    require(limits["logical_cpus"] >= 4 and limits["available_ram_bytes"] >= 12 * 2**30
            and psutil.disk_usage(directory).free >= 10 * 2**30, "Insufficient isolated effective capacity")
    record["execution_admission"] = {"version": ADMISSION_VERSION, "session": ticket["session"],
        "source_space_revision": ticket["source_space_revision"], "deadline_epoch": ticket["deadline_epoch"],
        "dataset_sha256": DATA_SHA}
    temporary = directory / "onstate_campaign.tmp"
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(directory / "onstate_campaign.json")
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"state": "claimed_no_resume", "version": ADMISSION_VERSION, **admitted,
                   "source_space_revision": ticket["source_space_revision"], "dataset_sha256": DATA_SHA}, handle)
    runs.mkdir(exist_ok=False)
    require(durable_claim is not None, "Durable claim callback is required before dispatch")
    time.sleep(2.1)
    require(durable_claim() is True, "On-state claim must be durable before dispatch")
    grants = directory / "grants"
    grants.mkdir(exist_ok=False)
    for run in contract()["runs"]:
        validate_admission(ticket, ledger, current, time.time(), environment)
        output, grant = runs / run["name"], grants / (run["name"] + ".json")
        with grant.open("x", encoding="utf-8") as handle:
            json.dump({"version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger, "run": run,
                       "dataset_dir": str(dataset), "output_dir": str(output), "parent_pid": os.getpid(),
                       "parent_creation_time": psutil.Process().create_time(), "claim_file": str(claim),
                       "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}, handle, indent=2)
        child = {**child_environment(environment), "RL_ONSTATE_GRANT": str(grant)}
        if dispatch is None:
            run_bounded(command(run, output, dataset), directory / (run["name"] + ".log"),
                        child, admitted["deadline_epoch"])
        else:
            dispatch(command(run, output, dataset), run["name"], child)
        result = aggregate(directory)
        require(any(row["run"] == run["name"] for row in result["rows"]),
                "On-state run returned without complete contract-valid evidence")
        (directory / "partial_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    result = aggregate(directory)
    require(not result["missing_runs"], "Incomplete on-state matrix")
    (directory / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (directory / "goal_metrics.json").write_text(json.dumps(goal_projection(result), indent=2), encoding="utf-8")
    return result
