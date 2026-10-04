"""Private HF research worker: read-only status, bounded jobs, durable artifacts.

No public execution endpoint. Credentials stay in this parent and are stripped
from training/browser child environments.
"""
from datetime import datetime, timezone
import hashlib
import http.server
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

from research.browser_bridge import ROOT

ALLOWED_ARTIFACT_SUFFIXES = {".json", ".jsonl", ".csv", ".log", ".png", ".zip", ".pkl", ".pt"}
FINAL_PHASES = {"preflight_complete", "pilot_complete", "timing_complete", "failed", "budget_stopped", "interrupted"}
APPEND_ONLY_SUFFIXES = {".log", ".csv", ".jsonl"}


def batch_deadline(start, max_hours, absolute_deadline=None):
    if not math.isfinite(start) or not math.isfinite(max_hours) or not 0 < max_hours <= 16:
        raise ValueError("Invalid persisted batch budget")
    deadline = start + max_hours * 3600
    if absolute_deadline is not None:
        absolute_deadline = float(absolute_deadline)
        if not math.isfinite(absolute_deadline) or absolute_deadline <= 0:
            raise ValueError("Invalid absolute campaign deadline")
        deadline = min(deadline, absolute_deadline)
    return deadline


def require_unattended_runtime(runtime):
    tier = runtime.hardware or runtime.requested_hardware
    replicas = runtime.raw.get("replicas", {})
    if tier != "cpu-upgrade":
        raise RuntimeError("Worker expects the authorized CPU Upgrade allocation")
    # HF omits gcTimeout after set_space_sleep_time(-1); on paid hardware
    # that means the documented never-sleep default, not a finite timeout.
    if runtime.sleep_time not in (-1, None):
        raise RuntimeError("Unattended research requires the provider never-sleep policy")
    # The provider can report zero ready replicas while this container starts.
    if replicas.get("requested") != 1 or replicas.get("current", 1) not in (0, 1):
        raise RuntimeError("Unattended research requires exactly one replica")
    return {"hardware": tier, "sleep_time": runtime.sleep_time,
            "sleep_policy": "never", "replicas": 1}


def copy_artifact(source, target, status_path):
    """Snapshot complete text lines even while a telemetry file is appending."""
    stat = source.stat()
    append_only = source.suffix in APPEND_ONLY_SUFFIXES
    if not append_only and source != status_path and time.time() - stat.st_mtime < 2:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if append_only:
        with source.open("rb") as incoming, target.open("wb") as outgoing:
            remaining = stat.st_size
            while remaining:
                chunk = incoming.read(min(remaining, 1024 * 1024))
                if not chunk:
                    break
                outgoing.write(chunk)
                remaining -= len(chunk)
        # Drop an unfinished final record, preserving a valid prefix.
        with target.open("r+b") as stream:
            end = stream.seek(0, os.SEEK_END)
            while end:
                start = max(0, end - 4096)
                stream.seek(start)
                tail = stream.read(end - start)
                newline = tail.rfind(b"\n")
                if newline >= 0:
                    stream.truncate(start + newline + 1)
                    break
                end = start
            else:
                stream.truncate(0)
        return True
    shutil.copyfile(source, target)
    after = source.stat()
    if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        target.unlink()
        return False
    return True


def sanitized(message):
    text = str(message)
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "RL_CONTROL_TOKEN"):
        value = os.environ.get(key)
        if value:
            text = text.replace(value, "[redacted]")
    return text[:4000]


class Worker:
    def __init__(self):
        from huggingface_hub import HfApi
        self.space = os.environ["RL_SPACE_ID"]
        self.artifact_repo = os.environ["RL_ARTIFACT_REPO"]
        self.session = os.environ["RL_SESSION_ID"]
        if not self.session.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Invalid artifact session")
        self.mode = os.environ.get("RL_MODE", "preflight")
        if self.mode not in ("preflight", "pilot", "timing_preflight", "timing_study"):
            raise ValueError("Unknown bounded research mode")
        if self.mode.startswith("timing_"):
            from research.timing_execution import SPACE, ARTIFACT_REPO
            if self.space != SPACE or self.artifact_repo != ARTIFACT_REPO or not self.session.startswith("timing-"):
                raise ValueError("Timing modes require a fresh session on the owned private targets")
        self.api = HfApi(token=os.environ["HF_TOKEN"])
        self.max_hours = min(float(os.environ.get("RL_MAX_HOURS", "16")), 16.0)
        if not 0 < self.max_hours <= 16:
            raise ValueError("Invalid runtime cap")
        self.artifacts = ROOT / "artifacts"
        self.artifacts.mkdir(exist_ok=True)
        self.control = self.artifacts / "control"
        self.control.mkdir(exist_ok=True)
        self.state_path = self.control / "status.json"
        self.state_lock = threading.Lock()
        self.sync_lock = threading.Lock()
        self.stop = threading.Event()
        self.process = None
        self.status = {"session": self.session, "mode": self.mode, "phase": "booting",
                       "hardware": "cpu-upgrade", "runtime_cap_hours": self.max_hours}

    def write_status(self, **fields):
        with self.state_lock:
            self.status.update(fields, updated_utc=datetime.now(timezone.utc).isoformat())
            temporary = self.state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.status, indent=2), encoding="utf-8")
            temporary.replace(self.state_path)
        print(json.dumps(fields), flush=True)

    def restore_status(self):
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError
        try:
            file = hf_hub_download(self.artifact_repo, repo_type="dataset",
                                   filename=f"{self.session}/control/status.json")
        except EntryNotFoundError:
            return None
        return json.loads(Path(file).read_text(encoding="utf-8"))

    def sync(self):
        with self.sync_lock, tempfile.TemporaryDirectory(prefix="rl-artifact-snapshot-") as folder:
            snapshot = Path(folder)
            for source in self.artifacts.rglob("*"):
                if not source.is_file() or source.is_symlink() or source.suffix not in ALLOWED_ARTIFACT_SUFFIXES:
                    continue
                target = snapshot / source.relative_to(self.artifacts)
                copy_artifact(source, target, self.state_path)
            if any(snapshot.rglob("*")):
                self.api.upload_folder(repo_id=self.artifact_repo, repo_type="dataset",
                                       folder_path=snapshot, path_in_repo=self.session,
                                       commit_message=f"Research artifact snapshot: {self.session}")

    def bounded_sync(self, timeout=20):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Invalid artifact flush timeout")
        result = {}

        def upload():
            try:
                self.sync()
                result["complete"] = True
            except Exception as error:
                result["error"] = sanitized(error)

        backup = threading.Thread(target=upload, daemon=True)
        backup.start()
        backup.join(timeout=timeout)
        if backup.is_alive():
            print("Artifact flush timed out; pause takes precedence over upload", flush=True)
            return False
        if "error" in result:
            print("Artifact flush failed:", result["error"], flush=True)
            return False
        return result.get("complete", False)

    def flush_and_pause(self):
        try:
            self.bounded_sync()
        finally:
            self.pause()

    def pause(self):
        try:
            self.api.pause_space(self.space)
        except Exception as error:
            print("Automatic pause failed:", sanitized(error), flush=True)
            # Exiting yields a stopped/error runtime rather than an indefinitely
            # running paid status server. Operator should verify via HF CLI.
            os._exit(1)

    def run_command(self, args, name, environment=None):
        self.write_status(phase=name, command=[str(a) for a in args])
        from research.timing_execution import child_environment, FINALIZATION_SECONDS
        environment = child_environment(os.environ if environment is None else environment)
        log = self.artifacts / (name + ".log")
        with log.open("a", encoding="utf-8") as handle:
            self.process = subprocess.Popen(args, cwd=ROOT, env=environment, stdout=handle,
                                            stderr=subprocess.STDOUT, start_new_session=True)
            while self.process.poll() is None:
                expired = (self.mode.startswith("timing_")
                           and time.time() >= self.deadline - FINALIZATION_SECONDS)
                if expired or self.stop.wait(1):
                    self.terminate_owned_job()
                    raise TimeoutError("Runtime budget reached")
            code = self.process.returncode
            self.process = None
        if code:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
            print("\n".join(sanitized(line) for line in tail), flush=True)
            raise RuntimeError(f"{name} exited with code {code}")
        print(f"Completed {name}", flush=True)

    def terminate_owned_job(self):
        if self.process is not None and self.process.poll() is None:
            import signal
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)

    def watchdog(self):
        from research.timing_execution import FINALIZATION_SECONDS
        timing = self.mode.startswith("timing_")
        while not self.stop.wait(1 if timing else 10):
            if time.time() >= self.deadline - (FINALIZATION_SECONDS if timing else 0):
                self.stop.set()
                self.terminate_owned_job()
                self.write_status(phase="budget_stopped")
                # A stuck upload must not defeat the spending bound.
                self.flush_and_pause()
                return

    def periodic_sync(self):
        failures = 0
        while not self.stop.wait(120):
            try:
                self.sync()
                failures = 0
            except Exception as error:
                failures += 1
                print("Artifact sync failed:", sanitized(error), flush=True)
                if failures >= 3:
                    self.stop.set()
                    self.terminate_owned_job()
                    self.write_status(phase="failed", error="Repeated artifact synchronization failure")
                    self.pause()
                    return

    def run(self):
        if self.mode.startswith("timing_"):
            from deploy.timing_worker import run_timing
            run_timing(self)
            return
        from research.provenance import fingerprint
        from research.resources import hardware
        previous = self.restore_status()
        if previous:
            if previous["phase"] not in FINAL_PHASES:
                self.write_status(phase="interrupted", error="Previous worker stopped mid-job; no silent restart/resume")
                self.flush_and_pause(); return
            if self.mode == "preflight" or previous["phase"] != "preflight_complete":
                self.status.update(previous)
                self.pause(); return
            original_start = previous["campaign_budget_start_epoch"]
        else:
            original_start = time.time()
        self.deadline = batch_deadline(
            original_start, self.max_hours, os.environ.get("RL_DEADLINE_EPOCH"))
        if time.time() >= self.deadline:
            self.write_status(phase="budget_stopped", error="Persisted wall-clock budget expired")
            self.flush_and_pause(); return
        runtime_policy = require_unattended_runtime(self.api.get_space_runtime(self.space))
        self.write_status(campaign_budget_start_epoch=original_start, deadline_epoch=self.deadline,
                          provenance=fingerprint(), host=hardware(), runtime_policy=runtime_policy)
        # Prove durable write access without an unbounded upload before the watchdog.
        if not self.bounded_sync():
            raise RuntimeError("Initial durable artifact synchronization failed or timed out")
        threading.Thread(target=self.watchdog, daemon=True).start()
        threading.Thread(target=self.periodic_sync, daemon=True).start()
        try:
            if self.mode == "preflight":
                self.run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], "unit_tests")
                self.run_command(["node", "tests/collision_memo.test.js"], "collision_tests")
                self.run_command([sys.executable, "-m", "research.fast_fidelity", "--headless"], "fidelity")
                self.run_command([sys.executable, "-m", "research.benchmark", "--fast"], "benchmark")
                self.run_command([sys.executable, "-m", "research.resources", "--decisions", "128"], "resources")
                self.write_status(phase="preflight_complete")
            else:
                if not previous or previous["phase"] != "preflight_complete":
                    raise RuntimeError("Pilot cannot start without a successful persisted preflight")
                campaign = self.artifacts / "pilot_campaign"
                self.run_command([sys.executable, "-m", "research.campaign", "prepare", "--directory", str(campaign)], "prepare_campaign")
                self.run_command([sys.executable, "-m", "research.campaign", "execute", "--directory", str(campaign),
                                  "--max-workers", "1"], "pilot")
                self.run_command([sys.executable, "-m", "research.campaign", "summarize", "--directory", str(campaign)], "pilot_summary")
                self.write_status(phase="pilot_complete")
        except Exception as error:
            self.write_status(phase="failed", error=sanitized(error))
        finally:
            self.stop.set()
            self.terminate_owned_job()
            time.sleep(2.1)  # Let completed files pass the stable-file sync filter.
            self.flush_and_pause()


def serve(worker):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/status"):
                self.send_error(404); return
            with worker.state_lock:
                payload = json.dumps(worker.status, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 7860), Handler)
    def guarded_run():
        try:
            worker.run()
        except BaseException as error:
            worker.stop.set()
            worker.terminate_owned_job()
            worker.write_status(phase="failed", error=sanitized(error))
            worker.flush_and_pause()
    threading.Thread(target=guarded_run, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    worker = Worker()
    serve(worker)
