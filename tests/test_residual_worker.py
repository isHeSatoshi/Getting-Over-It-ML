from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.residual_worker import (durable_sync, pinned_context, preflight_commands,
                                    run_residual, validate_context, restore_prior)
from deploy.space_worker import Worker
from research.phase_controller import SOURCE_DATA_SHA
from research.residual_execution import PREFLIGHT_CHECKS
from research.residual_study import plan
from tests.test_residual_research import admission_fixture
from tests.test_timing_execution import CURRENT


def fixture(root, mode="residual_preflight"):
    worker = Worker.__new__(Worker)
    worker.mode, worker.session = mode, "residual-synthetic-1"
    worker.space, worker.artifact_repo = "isHeSatoshi/rl-over-it-poc-20261004", "isHeSatoshi/rl-over-it-research-artifacts"
    worker.max_hours, worker.deadline = 1., 3700.
    worker.artifacts, worker.state_path = Path(root), Path(root)/"status.json"
    worker.state_path.write_text('{"owned":"fixture"}')
    worker.stop, worker.status = threading.Event(), {}
    worker.api = Mock()
    worker.api.repo_info.return_value = SimpleNamespace(private=True, sha="a"*40)
    worker.api.get_space_runtime.return_value = SimpleNamespace(
        hardware="cpu-upgrade", requested_hardware="cpu-upgrade", sleep_time=None,
        raw={"replicas": {"requested": 1, "current": 1}}, stage="PAUSED")
    worker.restore_status = Mock(return_value=None)
    worker.watchdog, worker.run_command = Mock(), Mock()
    worker.bounded_sync = Mock(return_value=True)
    worker.write_status = Mock()
    worker.terminate_owned_job, worker.pause = Mock(), Mock()
    return worker


def context_fixture(preflight=True):
    ticket, ledger, environment = admission_fixture()
    environment["RL_MODE"] = "residual_preflight" if preflight else "residual_study"
    previous = {**deepcopy(ticket["preflight"]), "study_kind": "residual",
                "operator_context_revision": "c"*40}
    if preflight:
        ticket["preflight"] = None
    context = {"ticket": ticket, "ledger": ledger, "plan": plan(),
               "prior": {"session": ticket["session"], "files": {"data.npz": SOURCE_DATA_SHA, "manifest.json": "d"*64},
                         "dataset_revision": "e"*40}, "preflight_context_revision": "c"*40}
    return context, environment, previous


class ResidualWorkerTests(unittest.TestCase):
    def test_exact_preflight_set_never_requests_full_training(self):
        with tempfile.TemporaryDirectory() as folder:
            commands = preflight_commands(fixture(folder), Path(folder)/"prior")
            self.assertEqual(tuple(name for name, _ in commands), PREFLIGHT_CHECKS)
            self.assertTrue(all("--remote-training" not in args for _, args in commands))
            self.assertEqual(sum("research.residual_preflight" in args for _, args in commands), 3)

    def test_fresh_preflight_and_passed_study_context_bind_actual_revision(self):
        for preflight in (True, False):
            context, environment, previous = context_fixture(preflight)
            with tempfile.TemporaryDirectory() as folder:
                worker = fixture(folder, environment["RL_MODE"])
                with patch.dict("os.environ", environment), patch("deploy.residual_worker.time.time", return_value=200):
                    ticket = validate_context(worker, context, "b"*40, CURRENT, None if preflight else previous)
                    self.assertEqual(ticket["context_revision"], "b"*40)

    def test_wrong_source_missing_or_drifted_passed_preflight_blocks_study(self):
        context, environment, previous = context_fixture(False)
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder, "residual_study")
            with patch.dict("os.environ", environment), patch("deploy.residual_worker.time.time", return_value=200):
                with self.assertRaisesRegex(ValueError, "passed"):
                    validate_context(worker, context, "b"*40, CURRENT, None)
                context["preflight_context_revision"] = "wrong"
                with self.assertRaisesRegex(ValueError, "original"):
                    validate_context(worker, context, "b"*40, CURRENT, previous)
                context["preflight_context_revision"] = "c"*40
                worker.api.repo_info.return_value.sha = "f"*40
                with self.assertRaisesRegex(ValueError, "source"):
                    validate_context(worker, context, "b"*40, CURRENT, previous)

    def run_mock(self, worker, context, environment, **overrides):
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.dict("os.environ", environment))
            stack.enter_context(patch("deploy.residual_worker.remote_host", return_value=True))
            stack.enter_context(patch("deploy.residual_worker.time.time", return_value=200))
            stack.enter_context(patch("deploy.residual_worker.configure_http_requests"))
            stack.enter_context(patch("deploy.residual_worker.threading.Thread"))
            stack.enter_context(patch("deploy.residual_worker.pinned_context", return_value=(context, "b"*40)))
            stack.enter_context(patch("deploy.residual_worker.fingerprint", return_value=CURRENT))
            stack.enter_context(patch("deploy.residual_worker.restore_prior", return_value=worker.artifacts/"prior"))
            stack.enter_context(patch("deploy.residual_worker.durable_sync", side_effect=overrides.get("sync", lambda *a: True)))
            return run_residual(worker)

    def test_preflight_records_passed_checks_and_pauses_without_dispatching_training(self):
        context, environment, _ = context_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            self.run_mock(worker, context, environment)
            self.assertEqual([call.args[1] for call in worker.run_command.call_args_list], list(PREFLIGHT_CHECKS))
            worker.pause.assert_called_once()
            self.assertTrue(any(call.kwargs.get("phase") == "preflight_complete"
                                for call in worker.write_status.call_args_list))

    def test_first_failed_preflight_command_never_records_passed_gate_and_pauses(self):
        context, environment, _ = context_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            worker.run_command.side_effect = ValueError("fixture command failed")
            self.run_mock(worker, context, environment)
            self.assertEqual(worker.run_command.call_count, 1)
            self.assertFalse(any(call.kwargs.get("phase") == "preflight_complete"
                                 for call in worker.write_status.call_args_list))
            worker.pause.assert_called_once()

    def test_interrupted_failed_or_complete_work_never_relaunches(self):
        context, environment, _ = context_fixture(False)
        for phase in ("residual_dispatch", "residual_complete", "failed"):
            with tempfile.TemporaryDirectory() as folder:
                worker = fixture(folder, "residual_study")
                worker.restore_status.return_value = {"phase": phase}
                self.run_mock(worker, context, environment)
                worker.run_command.assert_not_called()
                worker.pause.assert_called_once()

    def test_missing_initial_backup_blocks_all_work_but_still_requests_pause(self):
        context, environment, _ = context_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            self.run_mock(worker, context, environment, sync=lambda *a: False)
            worker.run_command.assert_not_called()
            worker.pause.assert_called_once()

    def test_cleanup_exception_cannot_skip_pause(self):
        context, environment, _ = context_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            worker.restore_status.return_value = {"phase": "failed"}
            worker.terminate_owned_job.side_effect = OSError("cleanup fixture")
            with self.assertRaises(OSError):
                self.run_mock(worker, context, environment)
            worker.pause.assert_called_once()

    def test_durable_required_file_missing_or_changed_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            path = worker.state_path
            payload = path.read_bytes()
            blob = hashlib.sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()
            worker.api.repo_info.return_value = SimpleNamespace(private=True, sha="a"*40, siblings=[
                SimpleNamespace(rfilename=f"{worker.session}/status.json", size=len(payload), lfs=None, blob_id=blob)])
            old = 3000-10  # File age must be consistent with the frozen clock patched below.
            os.utime(path, (old, old))
            with patch("deploy.residual_worker.time.time", return_value=3000):
                self.assertTrue(durable_sync(worker, [path]))
                worker.api.repo_info.return_value.siblings[0].blob_id = "wrong"
                with self.assertRaisesRegex(ValueError, "hash"):
                    durable_sync(worker, [path])
                worker.api.repo_info.return_value.siblings = []
                with self.assertRaisesRegex(ValueError, "missing"):
                    durable_sync(worker, [path])

    def test_restore_prior_rejects_foreign_session_or_changed_existing_file(self):
        context, _, _ = context_fixture(False)
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder, "residual_study")
            context["prior"]["session"] = "other"
            with self.assertRaises(ValueError):
                restore_prior(worker, context, CURRENT)
            context["prior"]["session"] = worker.session
            target = worker.artifacts/"residual_prior"
            target.mkdir()
            (target/"data.npz").write_bytes(b"changed")
            (target/"manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "drift"):
                restore_prior(worker, context, CURRENT)

    def test_new_dispatch_route_and_terminal_status_only(self):
        worker = Worker.__new__(Worker)
        worker.mode = "residual_study"
        with patch("deploy.residual_worker.run_residual") as run:
            worker.run()
            run.assert_called_once_with(worker)

    def test_expired_deadline_never_opens_context_and_pauses(self):
        context, environment, _ = context_fixture()
        environment["RL_DEADLINE_EPOCH"] = "200"
        with tempfile.TemporaryDirectory() as folder:
            worker = fixture(folder)
            with patch("deploy.residual_worker.pinned_context") as read:
                self.run_mock(worker, context, environment)
            worker.run_command.assert_not_called()
            worker.pause.assert_called_once()


if __name__ == "__main__":
    unittest.main()
