"""Fresh parent-bound residual admission and durable no-resume dispatch."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import psutil

from research.campaign import digest
from research.demonstrations import require
from research.onstate_execution import child_environment
from research.phase_controller import SOURCE_DATA_SHA
from research.provenance import fingerprint
from research.residual_study import SEEDS, plan
from research.resources import effective_limits
from research.timing_campaign import PROVENANCE_KEYS
from research.timing_execution import (FINALIZATION_SECONDS, remote_host, run_bounded,
                                       validate_study_admission)

VERSION = "residual-execution-admission-v1"
PREFLIGHT_CHECKS = ("unit_tests", "collision_tests", "resources", "benchmark",
                    "residual_zero_fidelity", "residual_pipeline", "residual_optimizer_smoke")
_TOKEN = object()


def validate_admission(ticket, ledger, current, now, environment):
    admitted = validate_study_admission(ticket, ledger, current, now, environment,
        version=VERSION, prefix="residual-", study_contract=plan(), preflight_checks=PREFLIGHT_CHECKS)
    require(environment.get("RL_MODE") == "residual_study"
            and ticket["deadline_epoch"]-ticket["start_epoch"] <= 7200
            and admitted["reserved_maximum_cost"] <= .06
            and now < ticket["deadline_epoch"]-FINALIZATION_SECONDS
            and ticket["prior_data_sha256"] == ticket["preflight"]["prior_data_sha256"] == SOURCE_DATA_SHA,
            "Residual mode/cleanup/prior/two-hour budget mismatch")
    batch = next(row for row in ledger["batches"] if row["session"] == ticket["session"])
    require(batch["maximum_estimated_compute_cost"] <= .06
            and isinstance(ticket["context_revision"], str) and len(ticket["context_revision"]) == 40
            and all(char in "0123456789abcdef" for char in ticket["context_revision"])
            and environment.get("RL_CONTEXT_REVISION") == ticket["context_revision"],
            "Residual reservation ceiling/context drift")
    return admitted


class RunPermit:
    def __init__(self, payload, environment, token=None):
        require(token is _TOKEN, "Residual permits come only from the validated loader")
        self.payload, self.environment = payload, environment

    def verify(self, seed):
        require(remote_host(self.environment) and self.environment.get("RL_MODE") == "residual_study"
                and seed == self.payload["seed"] and seed in SEEDS
                and os.getppid() == self.payload["parent_pid"]
                and psutil.Process(os.getppid()).create_time() == self.payload["parent_creation_time"],
                "Full residual work requires exact live isolated Linux parent/seed")
        require(time.time() < self.payload["ticket"]["deadline_epoch"]-FINALIZATION_SECONDS,
                "Residual cleanup reserve reached")
        claim = Path(self.payload["claim_file"])
        require(claim.is_file() and not claim.is_symlink()
                and hashlib.sha256(claim.read_bytes()).hexdigest() == self.payload["claim_sha256"],
                "Residual interruption claim changed")

    def record(self):
        return {"version": VERSION, "seed": self.payload["seed"],
                **{key: self.payload["ticket"][key] for key in
                   ("session", "source_space_revision", "deadline_epoch", "prior_data_sha256")}}


def require_permit(permit, seed):
    require(type(permit) is RunPermit, "Full residual stages need validated parent permit")
    permit.verify(seed)


def load_trainer_grant(args, environment=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment) and environment.get("RL_MODE") == "residual_study",
            "Full residual training is isolated Linux remote-only")
    path = Path(environment.get("RL_RESIDUAL_GRANT", ""))
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= 2*2**20, "Missing bounded residual grant")
    payload = json.loads(path.read_text())
    require(payload["version"] == VERSION and args.remote_training and not args.mock_smoke
            and args.seed == payload["seed"], "Wrong residual grant/version/arguments")
    validate_admission(payload["ticket"], payload["ledger"], fingerprint(), time.time(), environment)
    output, prior = Path(args.output_dir), Path(args.prior)
    require(output.is_absolute() and output == Path(payload["output_dir"]) and not output.exists()
            and prior.is_absolute() and prior == Path(payload["prior_directory"]),
            "Changed fresh residual output/prior paths")
    claim = Path(payload["claim_file"])
    require(claim.is_absolute() and claim.parent == output.parent.parent, "Residual claim outside campaign")
    archive = prior/"data.npz"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= 32*2**20
            and hashlib.sha256(archive.read_bytes()).hexdigest() == SOURCE_DATA_SHA,
            "Residual source trajectory archive changed")
    require(Path(payload["claim_file"]).is_file()
            and psutil.Process(os.getppid()).create_time() == payload["parent_creation_time"],
            "Residual parent creation time/claim changed")
    permit = RunPermit(payload, environment, _TOKEN)
    permit.verify(args.seed)
    return permit


def execute(directory, prior, ticket, ledger, *, durable_claim, durable_run, auto_pause,
            environment=None, dispatch=None):
    """No HF writes here: the owned deployment worker supplies durable callbacks."""
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment), "Residual dispatch is isolated Linux remote-only")
    directory, prior = Path(directory), Path(prior)
    require(directory.is_absolute() and prior.is_absolute(), "Absolute prepared campaign/prior required")
    current = fingerprint()
    admitted = validate_admission(ticket, ledger, current, time.time(), environment)
    record = json.loads((directory/"residual_campaign.json").read_text())
    require(record["plan"] == plan()
            and all(record["provenance"][key] == current[key] for key in PROVENANCE_KEYS),
            "Prepared residual plan/source drift")
    require(callable(auto_pause), "Owned Space auto-pause callback required")
    claim, runs, grants = directory/"execution_claim.json", directory/"runs", directory/"grants"
    require(not claim.exists() and not runs.exists() and not grants.exists(),
            "Existing residual work cannot silently resume")
    with claim.open("x") as stream:
        json.dump({"state": "claimed_no_resume", "version": VERSION, **admitted}, stream)
    runs.mkdir()
    grants.mkdir()
    try:
        require(durable_claim() is True, "Residual claim must be durable before any dispatch")
        limits = effective_limits()
        require(limits["logical_cpus"] >= 4 and limits["available_ram_bytes"] >= 12*2**30
                and psutil.disk_usage(directory).free >= 10*2**30, "Insufficient isolated residual resources")
        for seed in SEEDS:
            validate_admission(ticket, ledger, current, time.time(), environment)
            output, grant = runs/f"seed{seed}", grants/f"seed{seed}.json"
            with grant.open("x") as stream:
                json.dump({"version": VERSION, "ticket": ticket, "ledger": ledger, "seed": seed,
                           "output_dir": str(output), "prior_directory": str(prior),
                           "parent_pid": os.getpid(), "parent_creation_time": psutil.Process().create_time(),
                           "claim_file": str(claim), "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}, stream)
            child = {**child_environment(environment), "RL_RESIDUAL_GRANT": str(grant)}
            command = [sys.executable, "-m", "research.residual_train", "--remote-training",
                       "--seed", str(seed), "--prior", str(prior), "--output-dir", str(output)]
            if dispatch is None:
                run_bounded(command, directory/f"seed{seed}.log", child, ticket["deadline_epoch"])
            else:
                dispatch(command, seed, child)
            from research.residual_campaign import validate_directory
            validate_directory(output, seed, current)
            require(durable_run(seed) is True, "Completed residual run must be durably backed up")
        from research.residual_campaign import aggregate
        summary = aggregate(directory)
        (directory/"summary.json").write_text(json.dumps(summary, indent=2))
        require(durable_run("summary") is True, "Residual campaign summary must be durable")
        return summary
    finally:
        require(auto_pause() is True, "Owned residual Space pause must be independently confirmed")
