from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.space_worker import Worker
from deploy.imitation_worker import pinned_file, preflight_commands, run_imitation, validate_context
from research.imitation_execution import PREFLIGHT_CHECKS
from tests.test_imitation_execution import DATA, admission_fixture
from tests.test_timing_execution import CURRENT


def worker_fixture(root, mode="imitation_preflight"):
    worker = Worker.__new__(Worker)
    worker.mode, worker.session = mode, "imitation-synthetic-1"
    worker.space = "isHeSatoshi/rl-over-it-poc-20261004"
    worker.artifact_repo = "isHeSatoshi/rl-over-it-research-artifacts"
    worker.max_hours, worker.deadline = 1.0, 3700.0
    worker.artifacts = Path(root);worker.stop = threading.Event();worker.status = {}
    worker.api = Mock()
    worker.api.repo_info.return_value = SimpleNamespace(sha="a" * 40)
    worker.api.get_space_runtime.return_value = SimpleNamespace(
        hardware="cpu-upgrade", requested_hardware="cpu-upgrade", sleep_time=None,
        raw={"replicas": {"requested": 1, "current": 1}})
    worker.restore_status = Mock(return_value=None)
    worker.watchdog, worker.periodic_sync = Mock(), Mock()
    worker.write_status, worker.run_command = Mock(), Mock()
    worker.bounded_sync = Mock(return_value=True)
    worker.terminate_owned_job, worker.flush_and_pause = Mock(), Mock()
    return worker


class ImitationWorkerTests(unittest.TestCase):
    def test_preflight_has_exact_nine_checks_and_only_bounded_smokes(self):
        with tempfile.TemporaryDirectory() as folder:
            commands = preflight_commands(worker_fixture(folder), Path(folder) / "data")
            self.assertEqual(tuple(name for name, _ in commands), PREFLIGHT_CHECKS)
            for name, args in commands:
                self.assertNotIn("--remote-training", args)
                if name.startswith("imitation_smoke"):
                    self.assertIn("--smoke", args)

    def test_source_context_and_passed_preflight_gate_study(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            context = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
            with patch.dict("os.environ", env), patch("deploy.imitation_worker.time.time", return_value=200.0):
                self.assertEqual(validate_context(worker, context, CURRENT, None)["session"], worker.session)
                worker.api.repo_info.return_value.sha = "b" * 40
                with self.assertRaisesRegex(ValueError, "deployed"):
                    validate_context(worker, context, CURRENT, None)
                worker.mode = "imitation_study"
                with self.assertRaisesRegex(ValueError, "passed imitation"):
                    validate_context(worker, {"ticket": ticket, "ledger": ledger}, CURRENT, None)

    def test_mocked_preflight_is_durable_then_pauses_without_full_training(self):
        ticket, ledger, env = admission_fixture()
        context = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder);events = []
            worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            worker.run_command.side_effect = lambda args, name: events.append(name)
            with patch.dict("os.environ", env), \
                    patch("deploy.imitation_worker.time.time", return_value=200.0), \
                    patch("deploy.imitation_worker.time.sleep"), \
                    patch("deploy.imitation_worker.threading.Thread"), \
                    patch("deploy.imitation_worker.pinned_context", return_value=(context, "b" * 40)), \
                    patch("deploy.imitation_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.imitation_worker.restore_dataset", return_value=Path(folder) / "data"):
                run_imitation(worker)
            self.assertEqual(events, ["sync", *PREFLIGHT_CHECKS])
            self.assertTrue(any(c.kwargs.get("phase") == "preflight_complete"
                                for c in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_study_requires_durable_dispatch_before_mocked_executor(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "imitation_study")
            worker.restore_status.return_value = {**deepcopy(ticket["preflight"]), "study_kind": "imitation"}
            events = [];worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            with patch.dict("os.environ", env), \
                    patch("deploy.imitation_worker.time.time", return_value=200.0), \
                    patch("deploy.imitation_worker.time.sleep"), \
                    patch("deploy.imitation_worker.threading.Thread"), \
                    patch("deploy.imitation_worker.pinned_context", return_value=(
                        {"ticket": ticket, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.imitation_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.imitation_worker.restore_dataset", return_value=Path(folder) / "data"), \
                    patch("deploy.imitation_worker.restore_timing", return_value=Path(folder) / "prior"), \
                    patch("deploy.imitation_worker.prepare"), \
                    patch("deploy.imitation_worker.execute", side_effect=lambda *a, **k: events.append("execute")):
                run_imitation(worker)
            self.assertEqual(events, ["sync", "sync", "execute"])
            self.assertTrue(any(c.kwargs.get("phase") == "imitation_complete"
                                for c in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_interruption_and_terminal_states_never_relaunch(self):
        ticket, ledger, env = admission_fixture()
        for phase in ("imitation_dispatch", "imitation_complete", "failed"):
            with tempfile.TemporaryDirectory() as folder:
                worker = worker_fixture(folder, "imitation_study")
                worker.restore_status.return_value = {"phase": phase}
                with patch.dict("os.environ", env), \
                        patch("deploy.imitation_worker.time.time", return_value=200.0), \
                        patch("deploy.imitation_worker.time.sleep"), \
                        patch("deploy.imitation_worker.threading.Thread"), \
                        patch("deploy.imitation_worker.pinned_context", return_value=(
                            {"ticket": ticket, "ledger": ledger}, "b" * 40)):
                    run_imitation(worker)
                worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_initial_sync_failure_never_imports_or_runs_and_still_pauses(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder);worker.bounded_sync.return_value = False
            with patch.dict("os.environ", env), \
                    patch("deploy.imitation_worker.time.time", return_value=200.0), \
                    patch("deploy.imitation_worker.time.sleep"), \
                    patch("deploy.imitation_worker.threading.Thread"), \
                    patch("deploy.imitation_worker.pinned_context", return_value=(
                        {"ticket": {**ticket, "preflight": None}, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.imitation_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.imitation_worker.restore_dataset") as restore:
                run_imitation(worker)
            restore.assert_not_called();worker.run_command.assert_not_called()
            worker.flush_and_pause.assert_called_once()

    def test_private_file_byte_limit_is_checked_before_download(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            worker.api.repo_info.return_value = SimpleNamespace(siblings=[
                SimpleNamespace(rfilename="owned/file.json", size=100)])
            with patch("huggingface_hub.hf_hub_download") as download:
                with self.assertRaisesRegex(ValueError, "byte limit"):
                    pinned_file(worker, "a" * 40, "owned/file.json", 10)
                download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
