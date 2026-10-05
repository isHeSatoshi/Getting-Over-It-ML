"""Fresh ten-hour/$0.30 goal pilot admission, inherited owned execution safety."""
import hashlib
import json
import math
import os
from pathlib import Path
import time

import psutil

from research.campaign import digest
from research.demonstrations import require
from research.goal_study import plan, SEEDS
from research.phase_controller import SOURCE_DATA_SHA
from research.provenance import fingerprint
from research.timing_execution import (SPACE, ARTIFACT_REPO, FINALIZATION_SECONDS,
                                       remote_host, validate_study_admission)
from research.onstate_execution import child_environment

VERSION = "goal-sac-execution-v1"
CHECKS = ("unit_tests", "collision_tests", "resources", "benchmark",
          "goal_pipeline", "goal_prefix_fidelity")
_TOKEN = object()


def validate_admission(ticket, ledger, current, now, environment):
    result = validate_study_admission(ticket, ledger, current, now, environment,
        version=VERSION, prefix="goal-", study_contract=plan(), preflight_checks=CHECKS)
    require(environment.get("RL_MODE") == "goal_study"
            and ticket["deadline_epoch"]-ticket["start_epoch"] <= 36000
            and result["reserved_maximum_cost"] <= .30
            and now < ticket["deadline_epoch"]-FINALIZATION_SECONDS
            and ticket["prior_data_sha256"] == SOURCE_DATA_SHA
            and ticket["preflight"]["prior_data_sha256"] == SOURCE_DATA_SHA
            and isinstance(ticket["context_revision"], str) and len(ticket["context_revision"]) == 40
            and all(c in "0123456789abcdef" for c in ticket["context_revision"])
            and environment.get("RL_CONTEXT_REVISION") == ticket["context_revision"],
            "Goal pilot mode/time/cost/prior/context changed")
    row = next(row for row in ledger["batches"] if row["session"] == ticket["session"])
    require(row["maximum_estimated_compute_cost"] <= .30, "Goal reservation exceeds approved pilot")
    return result


class GoalPermit:
    def __init__(self, payload, environment, token=None):
        require(token is _TOKEN, "Goal permit requires the validated remote loader")
        self.payload, self.environment = payload, environment

    def verify(self, seed):
        require(remote_host(self.environment) and self.environment.get("RL_MODE") == "goal_study"
                and seed in SEEDS and seed == self.payload["seed"]
                and os.getppid() == self.payload["parent_pid"]
                and psutil.Process(os.getppid()).create_time() == self.payload["parent_creation_time"],
                "Goal training requires exact live isolated Linux parent")
        require(time.time() < self.payload["ticket"]["deadline_epoch"]-60, "Goal deadline cleanup reserve reached")
        path = Path(self.payload["claim_file"])
        require(path.is_file() and not path.is_symlink()
                and hashlib.sha256(path.read_bytes()).hexdigest() == self.payload["claim_sha256"],
                "Interrupted goal claim changed")


def load_permit(args):
    environment = dict(os.environ)
    require(remote_host(environment) and environment.get("RL_MODE") == "goal_study",
            "Full goal training is remote-only; no desktop training")
    path = Path(environment.get("RL_GOAL_GRANT", ""))
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= 2*2**20, "Missing bounded goal grant")
    payload = json.loads(path.read_text())
    require(payload["version"] == VERSION and args.seed == payload["seed"]
            and args.remote_training, "Goal grant arguments/version mismatch")
    validate_admission(payload["ticket"], payload["ledger"], fingerprint(), time.time(), environment)
    require(args.output_dir.is_absolute() and str(args.output_dir) == payload["output_dir"]
            and not args.output_dir.exists() and args.prior.is_absolute()
            and str(args.prior) == payload["prior_directory"], "Changed fresh goal output/prior")
    archive = args.prior/"data.npz"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= 32*2**20
            and hashlib.sha256(archive.read_bytes()).hexdigest() == SOURCE_DATA_SHA, "Changed scaffold archive")
    permit = GoalPermit(payload, environment, _TOKEN)
    permit.verify(args.seed)
    return permit, payload["preflight_physics_ticks"]
