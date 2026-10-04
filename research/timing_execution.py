"""Remote-only timing execution and parent-bound per-run trainer admission."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import psutil

from research.browser_bridge import ROOT
from research.campaign import digest
from research.provenance import fingerprint
from research.resources import effective_limits
from research.timing_campaign import PROVENANCE_KEYS, aggregate, command, contract, finite, require

SPACE = "isHeSatoshi/rl-over-it-poc-20261004"
ARTIFACT_REPO = "isHeSatoshi/rl-over-it-research-artifacts"
ADMISSION_VERSION = "timing-execution-admission-v1"
FINALIZATION_SECONDS = 60.0
PREFLIGHT_CHECKS = (
    "unit_tests", "collision_tests", "fidelity", "timing_fidelity",
    "benchmark", "resources", "timing_smoke_repeat_1", "timing_smoke_repeat_4",
)


def remote_host(environment):
    return sys.platform == "linux" and not environment.get("FACTORY_DESKTOP_CDP_PORT")


def validate_admission(ticket, ledger, current, now, environment):
    return validate_study_admission(
        ticket, ledger, current, now, environment, version=ADMISSION_VERSION,
        prefix="timing-", study_contract=contract(), preflight_checks=PREFLIGHT_CHECKS)


def validate_study_admission(ticket, ledger, current, now, environment, *,
                             version, prefix, study_contract, preflight_checks):
    """Check a parent's verified immutable context; no HF reads/writes or secrets."""
    require(ticket["version"] == version, "Invalid study admission version")
    session = ticket["session"]
    require(isinstance(session, str) and session.startswith(prefix)
            and session.replace("-", "").replace("_", "").isalnum(), "A fresh timing session is required")
    require(ticket["space"] == SPACE and ticket["artifact_repo"] == ARTIFACT_REPO,
            "Admission targets a different Space/artifact repo")
    require(ticket["contract_sha256"] == digest(study_contract), "Admission protocol differs from declared study")
    require(ticket["paused_before_launch"] is True, "Independently verified PAUSED admission is required")
    require(ticket["runtime_policy"] == {"hardware": "cpu-upgrade", "sleep_policy": "never", "replicas": 1},
            "Admission requires one never-sleep CPU Upgrade replica")
    require(environment.get("RL_SESSION_ID") == session
            and environment.get("RL_SPACE_ID") == SPACE
            and environment.get("RL_ARTIFACT_REPO") == ARTIFACT_REPO, "Configured worker session/targets differ")
    require(finite(now), "Invalid admission clock")
    selected = [batch for batch in ledger["batches"] if batch["session"] == session]
    require(len(selected) == 1, "A unique reserved session must exist in the cost ledger")
    batch = selected[0]
    start, deadline, rate = (batch[key] for key in ("start_epoch", "deadline_epoch", "rate_per_hour"))
    require(all(finite(value) for value in (start, deadline, rate)) and 0 < rate <= 0.03
            and 0 < deadline - start <= 16 * 3600 and start <= now < deadline,
            "Expired, oversized or invalid reserved timing budget")
    require(batch["verified_end_epoch"] is None and batch["tier"] == "cpu-upgrade"
            and batch["space"] == SPACE and batch["status"] == "reserved_preflight",
            "Session is closed, already started or not a preflight reservation")
    require(batch["source_space_revision"] == ticket["source_space_revision"],
            "Reservation and admitted source Space revision differ")
    expected_cost = (deadline - start) / 3600 * rate
    require(finite(batch["maximum_estimated_compute_cost"])
            and batch["maximum_estimated_compute_cost"] >= expected_cost,
            "Reservation does not cover its declared maximum wall time")
    ceiling = ledger["operating_ceiling"]
    require(ledger["currency"] == "USD" and finite(ceiling) and 0 < ceiling <= 10,
            "Invalid cumulative compute ceiling")
    costs = []
    for other in ledger["batches"]:
        if other["verified_end_epoch"] is None:
            require(other["session"] == session, "Another paid session is still active")
            cost = other["maximum_estimated_compute_cost"]
        else:
            cost = other["estimated_elapsed_compute_cost_upper_bound"]
        require(finite(cost) and cost >= 0, "Invalid cumulative ledger entry")
        costs.append(cost)
    require(sum(costs) <= ceiling, "Cumulative reserved/elapsed cost exceeds the operating ceiling")
    require(ticket["start_epoch"] == start and ticket["deadline_epoch"] == deadline
            and float(environment.get("RL_DEADLINE_EPOCH", "nan")) == deadline,
            "Persisted timing deadline/start changed")
    preflight = ticket["preflight"]
    require(preflight["phase"] == "preflight_complete" and preflight["session"] == session
            and preflight["deadline_epoch"] == deadline
            and preflight["campaign_budget_start_epoch"] == start
            and preflight["source_space_revision"] == ticket["source_space_revision"],
            "Missing or changed fresh-session preflight/source evidence")
    require(isinstance(ticket["source_space_revision"], str)
            and len(ticket["source_space_revision"]) == 40
            and all(c in "0123456789abcdef" for c in ticket["source_space_revision"]),
            "Invalid immutable source Space revision")
    require(set(preflight["checks"]) == set(preflight_checks)
            and all(preflight["checks"][name] is True for name in preflight_checks),
            "All declared timing-study remote preflight checks must pass")
    for key in PROVENANCE_KEYS:
        require(preflight["provenance"][key] == current[key], "Preflight source/game drift: " + key)
    return {"session": session, "deadline_epoch": deadline, "reserved_maximum_cost": expected_cost,
            "cumulative_reserved_or_elapsed_cost": sum(costs)}


def child_environment(environment):
    """Keep compute configuration, but not parent credential variables."""
    def credential(name):
        upper = name.upper()
        return any(marker in upper for marker in ("TOKEN", "PASSWORD", "SECRET", "API_KEY"))
    return {key: value for key, value in environment.items() if not credential(key)}


def terminate_owned_process(process):
    """Only the new process group launched below, never user/shared processes."""
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def run_bounded(args, log_path, environment, deadline):
    require(remote_host(environment), "Bounded process groups require the isolated Linux worker")
    cutoff = deadline - FINALIZATION_SECONDS
    require(time.time() < cutoff, "Timing deadline expired or cleanup reserve reached before subprocess launch")
    with Path(log_path).open("x", encoding="utf-8") as log:
        process = subprocess.Popen(args, cwd=ROOT, env=child_environment(environment),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            remaining = cutoff - time.time()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(args, 0)
            code = process.wait(timeout=remaining)
            require(code == 0, "Owned timing run failed; stop scheduling and preserve its log")
        finally:
            terminate_owned_process(process)


def load_trainer_grant(args, environment=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment), "Trainer timing admission requires an isolated Linux host")
    filename = environment.get("RL_TIMING_GRANT")
    require(filename, "Missing bounded runner admission grant")
    path = Path(filename)
    require(path.is_absolute() and not path.is_symlink(), "Invalid trainer grant path")
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(payload["version"] == ADMISSION_VERSION and payload["parent_pid"] == os.getppid(),
            "Trainer grant does not belong to the direct owned parent")
    validate_admission(payload["ticket"], payload["ledger"], fingerprint(), time.time(), environment)
    run = payload["run"]
    require(run in contract()["runs"] and args.algorithm == "ppo" and args.action == "absolute"
            and args.frame_skip == run["frame_skip"] and args.seed == run["seed"]
            and args.steps == run["steps"] and args.timing_study and args.remote_training and not args.smoke,
            "Trainer arguments differ from the admitted run")
    output = Path(args.output_dir or "")
    require(output.is_absolute() and output == Path(payload["output_dir"]) and not output.exists(),
            "Trainer output differs from the new admitted run directory")
    claim = Path(payload["claim_file"])
    require(claim.is_absolute() and claim.parent == output.parent.parent and claim.is_file()
            and hashlib.sha256(claim.read_bytes()).hexdigest() == payload["claim_sha256"],
            "Execution interruption claim is missing or changed")
    require(time.time() < payload["ticket"]["deadline_epoch"] - FINALIZATION_SECONDS,
            "Trainer timing budget reached its cleanup reserve")
    return {"version": ADMISSION_VERSION, "session": payload["ticket"]["session"],
            "source_space_revision": payload["ticket"]["source_space_revision"],
            "deadline_epoch": payload["ticket"]["deadline_epoch"], "run": run["name"]}


def execute(directory, ticket, ledger, environment=None, dispatch=None, durable_claim=None):
    environment = dict(os.environ if environment is None else environment)
    require(remote_host(environment),
            "Timing-study execution is isolated Linux remote-only, never desktop training")
    directory = Path(directory)
    require(directory.is_absolute(), "Use an absolute prepared timing directory")
    current = fingerprint()
    admitted = validate_admission(ticket, ledger, current, time.time(), environment)
    record = json.loads((directory / "timing_campaign.json").read_text(encoding="utf-8"))
    require(record["contract"] == contract(), "Prepared timing protocol changed")
    for key in PROVENANCE_KEYS:
        require(record["provenance"][key] == current[key], "Prepared source/game drift: " + key)
    # A single exclusive claim persists interruption evidence before any learner.
    # Existing runs/claim block both checkpoint resume and fresh reruns in-place.
    runs, claim = directory / "runs", directory / "execution_claim.json"
    require(not runs.exists() and not claim.exists(), "Existing execution/run state cannot silently resume")
    limits = effective_limits()
    require(limits["logical_cpus"] >= 4 and limits["available_ram_bytes"] >= 12 * 2**30,
            "Insufficient effective CPU/RAM for one timing learner plus reference")
    require(psutil.disk_usage(directory).free >= 10 * 2**30, "Insufficient free artifact disk")
    record["execution_admission"] = {"version": ADMISSION_VERSION, "session": ticket["session"],
                                   "source_space_revision": ticket["source_space_revision"],
                                   "deadline_epoch": ticket["deadline_epoch"]}
    temporary = directory / "timing_campaign.tmp"
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(directory / "timing_campaign.json")
    with claim.open("x", encoding="utf-8") as handle:
        json.dump({"version": ADMISSION_VERSION, **admitted, "state": "claimed_no_resume",
                   "source_space_revision": ticket["source_space_revision"]}, handle, indent=2)
    runs.mkdir(exist_ok=False)
    if durable_claim is not None:
        # Give the immutable newly written claim the stable-copy interval;
        # timing worker watchdog remains active and preserves its cleanup reserve.
        time.sleep(2.1)
        require(durable_claim() is True, "Execution claim must be durable before learner dispatch")
    grants = directory / "grants"
    grants.mkdir(exist_ok=False)
    for run in record["contract"]["runs"]:
        validate_admission(ticket, ledger, current, time.time(), environment)
        output = runs / run["name"]
        grant = grants / (run["name"] + ".json")
        with grant.open("x", encoding="utf-8") as handle:
            json.dump({"version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger,
                       "run": run, "output_dir": str(output), "parent_pid": os.getpid(),
                       "claim_file": str(claim),
                       "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}, handle, indent=2)
        run_environment = {**environment, "RL_TIMING_GRANT": str(grant)}
        if dispatch is None:
            run_bounded(command(run, output), directory / (run["name"] + ".log"),
                        run_environment, admitted["deadline_epoch"])
        else:
            dispatch(command(run, output), run["name"], run_environment)
        result = aggregate(directory)
        require(any(row["run"] == run["name"] for row in result["rows"]),
                "Run returned without complete contract-valid evidence")
        (directory / "partial_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    result = aggregate(directory)
    require(not result["missing_runs"], "Timing matrix ended incomplete")
    (directory / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
