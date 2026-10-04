"""Linux-only imitation execution and direct-parent, data-bound run grants."""
import hashlib
import json
import os
from pathlib import Path
import time

import psutil

from research.demonstrations import require
from research.imitation_campaign import aggregate, command, contract, dataset_contract
from research.provenance import fingerprint
from research.resources import effective_limits
from research.timing_campaign import PROVENANCE_KEYS
from research.timing_execution import (
    ARTIFACT_REPO, SPACE, FINALIZATION_SECONDS, remote_host, run_bounded,
    validate_study_admission)

ADMISSION_VERSION = "imitation-execution-admission-v1"
_PERMIT_TOKEN = object()
PREFLIGHT_CHECKS = (
    "unit_tests", "collision_tests", "fidelity", "timing_fidelity", "benchmark", "resources",
    "imitation_smoke_scratch", "imitation_smoke_bc", "imitation_smoke_bc_ppo",
)


def validate_admission(ticket, ledger, current, now, environment):
    result = validate_study_admission(
        ticket, ledger, current, now, environment, version=ADMISSION_VERSION,
        prefix="imitation-", study_contract=contract(), preflight_checks=PREFLIGHT_CHECKS)
    require(isinstance(ticket.get("dataset"), dict)
            and ticket["dataset"] == ticket["preflight"].get("dataset"),
            "Admission corpus/normalization differs from passed preflight")
    return result


class RunPermit:
    """Internal capability from an authenticated parent grant, not an arbitrary JSON flag."""
    def __init__(self, payload, environment, token=None):
        require(token is _PERMIT_TOKEN, "Only the validated grant loader creates run permits")
        self.payload, self.environment = payload, environment
        self.run = payload["run"]

    def verify(self, arm, seed, dataset_sha256=None):
        require(remote_host(self.environment) and os.getppid() == self.payload["parent_pid"],
                "Imitation stages require their direct isolated Linux parent")
        require(arm == self.run["arm"] and seed == self.run["seed"],
                "Stage differs from admitted imitation arm/seed")
        require(time.time() < self.payload["ticket"]["deadline_epoch"] - FINALIZATION_SECONDS,
                "Imitation stage reached the cleanup reserve")
        claim = Path(self.payload["claim_file"])
        require(claim.is_file() and hashlib.sha256(claim.read_bytes()).hexdigest()
                == self.payload["claim_sha256"], "Imitation interruption claim changed")
        if dataset_sha256 is not None:
            require(dataset_sha256 == self.payload["ticket"]["dataset"]["data_sha256"],
                    "Trainer loaded a different corpus")

    def record(self):
        ticket = self.payload["ticket"]
        return {"version": ADMISSION_VERSION, "session": ticket["session"],
                "source_space_revision": ticket["source_space_revision"],
                "deadline_epoch": ticket["deadline_epoch"], "run": self.run["name"],
                "dataset_sha256": ticket["dataset"]["data_sha256"]}


def load_trainer_grant(args, environment=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment), "Full imitation training is isolated Linux remote-only")
    filename = environment.get("RL_IMITATION_GRANT", "")
    path = Path(filename)
    require(filename and path.is_absolute() and not path.is_symlink()
            and path.stat().st_size <= 2 * 2**20, "Missing or oversized parent imitation grant")
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(payload["version"] == ADMISSION_VERSION and payload["parent_pid"] == os.getppid(),
            "Imitation grant does not belong to the direct owned parent")
    validate_admission(payload["ticket"], payload["ledger"], fingerprint(), time.time(), environment)
    run = payload["run"]
    require(run in contract()["runs"] and args.arm == run["arm"] and args.seed == run["seed"]
            and args.remote_training and not args.smoke, "Trainer arguments differ from admitted run")
    output, dataset = Path(args.output_dir or ""), Path(args.dataset)
    require(output.is_absolute() and output == Path(payload["output_dir"]) and not output.exists()
            and dataset.is_absolute() and dataset == Path(payload["dataset_dir"]),
            "Trainer output/data paths differ from fresh grant")
    claim = Path(payload["claim_file"])
    require(claim.is_absolute() and claim.parent == output.parent.parent and not claim.is_symlink(),
            "Wrong imitation claim location")
    permit = RunPermit(payload, environment, _PERMIT_TOKEN)
    permit.verify(args.arm, args.seed)
    return permit


def require_permit(permit, arm, seed):
    require(type(permit) is RunPermit, "Full remote imitation stage requires a validated parent permit")
    permit.verify(arm, seed)


def execute(directory, dataset, ticket, ledger, environment=None, dispatch=None, durable_claim=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment), "Imitation execution is Linux remote-only, never desktop training")
    directory, dataset = Path(directory), Path(dataset)
    require(directory.is_absolute() and dataset.is_absolute(), "Use absolute campaign/data paths")
    current = fingerprint()
    admitted = validate_admission(ticket, ledger, current, time.time(), environment)
    record = json.loads((directory / "imitation_campaign.json").read_text(encoding="utf-8"))
    require(record["contract"] == contract(), "Prepared imitation protocol changed")
    for key in PROVENANCE_KEYS:
        require(record["provenance"][key] == current[key], "Prepared imitation source/assets changed")
    require(record["dataset"] == ticket["dataset"] == dataset_contract(dataset, current),
            "Prepared/admitted/actual corpus or normalization differs")
    runs, claim = directory / "runs", directory / "execution_claim.json"
    require(not runs.exists() and not claim.exists(), "Existing imitation execution cannot silently resume")
    limits = effective_limits()
    require(limits["logical_cpus"] >= 4 and limits["available_ram_bytes"] >= 12 * 2**30
            and psutil.disk_usage(directory).free >= 10 * 2**30,
            "Insufficient effective capacity for isolated imitation training")
    record["execution_admission"] = {
        "version": ADMISSION_VERSION, "session": ticket["session"],
        "source_space_revision": ticket["source_space_revision"], "deadline_epoch": ticket["deadline_epoch"],
        "dataset_sha256": ticket["dataset"]["data_sha256"]}
    temporary = directory / "imitation_campaign.tmp"
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(directory / "imitation_campaign.json")
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"version": ADMISSION_VERSION, **admitted, "state": "claimed_no_resume",
                   "source_space_revision": ticket["source_space_revision"],
                   "dataset_sha256": ticket["dataset"]["data_sha256"]}, handle, indent=2)
    runs.mkdir(exist_ok=False)
    require(durable_claim is not None, "A durable claim callback is required before imitation dispatch")
    time.sleep(2.1)
    require(durable_claim() is True, "Imitation execution claim must be durable before dispatch")
    grants = directory / "grants"; grants.mkdir(exist_ok=False)
    for run in record["contract"]["runs"]:
        validate_admission(ticket, ledger, current, time.time(), environment)
        output, grant = runs / run["name"], grants / (run["name"] + ".json")
        with grant.open("x", encoding="utf-8") as handle:
            json.dump({"version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger, "run": run,
                       "dataset_dir": str(dataset), "output_dir": str(output), "parent_pid": os.getpid(),
                       "claim_file": str(claim),
                       "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}, handle, indent=2)
        child = {**environment, "RL_IMITATION_GRANT": str(grant)}
        arguments = command(run, output, dataset)
        if dispatch is None:
            run_bounded(arguments, directory / (run["name"] + ".log"), child, ticket["deadline_epoch"])
        else:
            dispatch(arguments, run["name"], child)
        result = aggregate(directory)
        require(any(row["run"] == run["name"] for row in result["rows"]),
                "Imitation run lacks complete contract-valid artifacts")
        (directory / "partial_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    result = aggregate(directory)
    require(not result["missing_runs"], "Imitation matrix ended incomplete")
    (directory / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
