from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.onstate_worker import pinned_file, preflight_commands, run_onstate, validate_context
from deploy.space_worker import Worker
from research.onstate_execution import PREFLIGHT_CHECKS
from tests.test_imitation_worker import worker_fixture as old_worker
from tests.test_onstate_execution import admission_fixture
from tests.test_timing_execution import CURRENT


def worker_fixture(root, mode="onstate_preflight"):
    worker = old_worker(root)
    worker.mode, worker.session = mode, "onstate-synthetic-1"
    worker.api.repo_info.return_value.private = True
    return worker


class OnStateWorkerTests(unittest.TestCase):
    def test_exact_preflight_set_is_bounded_smoke_only(self):
        with tempfile.TemporaryDirectory() as folder:
            commands = preflight_commands(worker_fixture(folder), Path(folder) / "data")
            self.assertEqual(tuple(name for name, _ in commands), PREFLIGHT_CHECKS)
            for name, args in commands:
                self.assertNotIn("--remote-training", args)
                if name.startswith("onstate_smoke"):
                    self.assertIn("--smoke", args)
                    self.assertEqual(args[args.index("--seed")+1], "9")

    def test_missing_wrong_source_and_failed_preflight_block_study(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "onstate_study")
            with patch.dict("os.environ", env), patch("deploy.onstate_worker.time.time", return_value=200):
                with self.assertRaisesRegex(ValueError, "passed on-state"):
                    validate_context(worker, {"ticket": ticket, "ledger": ledger}, CURRENT, None)
                previous = {**deepcopy(ticket["preflight"]), "study_kind": "onstate"}
                worker.api.repo_info.return_value.sha = "b" * 40
                with self.assertRaisesRegex(ValueError, "source"):
                    validate_context(worker, {"ticket": ticket, "ledger": ledger}, CURRENT, previous)

    def test_fresh_preflight_records_checks_then_pauses_without_training(self):
        ticket, ledger, env = admission_fixture("onstate_preflight")
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            context = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
            with patch.dict("os.environ", env), \
                    patch("deploy.onstate_worker.time.time", return_value=200), \
                    patch("deploy.onstate_worker.time.sleep"), \
                    patch("deploy.onstate_worker.configure_http_requests"), \
                    patch("deploy.onstate_worker.threading.Thread"), \
                    patch("deploy.onstate_worker.pinned_context", return_value=(context, "b" * 40)), \
                    patch("deploy.onstate_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.onstate_worker.restore_dataset", return_value=Path(folder) / "data"):
                run_onstate(worker)
            self.assertEqual([call.args[1] for call in worker.run_command.call_args_list], list(PREFLIGHT_CHECKS))
            self.assertTrue(any(call.kwargs.get("phase") == "preflight_complete"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_existing_interrupted_terminal_or_failed_session_never_relaunches(self):
        ticket, ledger, env = admission_fixture()
        for phase in ("onstate_dispatch", "onstate_complete", "failed"):
            with tempfile.TemporaryDirectory() as folder:
                worker = worker_fixture(folder, "onstate_study")
                worker.restore_status.return_value = {"phase": phase}
                with patch.dict("os.environ", env), \
                        patch("deploy.onstate_worker.time.time", return_value=200), \
                        patch("deploy.onstate_worker.time.sleep"), \
                        patch("deploy.onstate_worker.configure_http_requests"), \
                        patch("deploy.onstate_worker.threading.Thread"), \
                        patch("deploy.onstate_worker.pinned_context") as context:
                    run_onstate(worker)
                context.assert_not_called()
                worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_study_needs_durable_dispatch_and_passing_preflight_then_pauses(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "onstate_study")
            worker.restore_status.return_value = {**deepcopy(ticket["preflight"]), "study_kind": "onstate"}
            events = []
            worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            with patch.dict("os.environ", env), \
                    patch("deploy.onstate_worker.time.time", return_value=200), \
                    patch("deploy.onstate_worker.time.sleep"), \
                    patch("deploy.onstate_worker.configure_http_requests"), \
                    patch("deploy.onstate_worker.threading.Thread"), \
                    patch("deploy.onstate_worker.pinned_context", return_value=(
                        {"ticket": ticket, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.onstate_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.onstate_worker.restore_dataset", return_value=Path(folder) / "data"), \
                    patch("deploy.onstate_worker.prepare"), \
                    patch("deploy.onstate_worker.execute", side_effect=lambda *a, **k: events.append("execute")):
                run_onstate(worker)
            self.assertEqual(events, ["sync", "sync", "execute"])
            self.assertTrue(any(call.kwargs.get("phase") == "onstate_complete"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_missing_first_backup_stops_before_data_restore_and_pauses(self):
        ticket, ledger, env = admission_fixture("onstate_preflight")
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            worker.bounded_sync.return_value = False
            with patch.dict("os.environ", env), \
                    patch("deploy.onstate_worker.time.time", return_value=200), \
                    patch("deploy.onstate_worker.time.sleep"), \
                    patch("deploy.onstate_worker.configure_http_requests"), \
                    patch("deploy.onstate_worker.threading.Thread"), \
                    patch("deploy.onstate_worker.pinned_context", return_value=(
                        {"ticket": {**ticket, "preflight": None}, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.onstate_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.onstate_worker.restore_dataset") as restore:
                run_onstate(worker)
            restore.assert_not_called()
            worker.run_command.assert_not_called()
            worker.flush_and_pause.assert_called_once()

    def test_nonprivate_and_oversized_files_refused_before_download(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            worker.api.repo_info.return_value = SimpleNamespace(private=False, siblings=[
                SimpleNamespace(rfilename="owned/file.json", size=100)])
            with patch("huggingface_hub.hf_hub_download") as download:
                with self.assertRaises(ValueError):
                    pinned_file(worker, "a" * 40, "owned/file.json", 1000)
                download.assert_not_called()
            worker.api.repo_info.return_value.private = True
            with patch("huggingface_hub.hf_hub_download") as download:
                with self.assertRaises(ValueError):
                    pinned_file(worker, "a" * 40, "owned/file.json", 10)
                download.assert_not_called()

    def test_worker_dispatch_uses_new_route_only(self):
        worker = Worker.__new__(Worker)
        worker.mode = "onstate_study"
        with patch("deploy.onstate_worker.run_onstate") as run:
            worker.run()
            run.assert_called_once_with(worker)

    def test_cleanup_failure_cannot_skip_final_pause(self):
        _, _, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "onstate_study")
            worker.restore_status.return_value = {"phase": "onstate_complete"}
            worker.terminate_owned_job.side_effect = OSError("owned fixture cleanup failure")
            with patch.dict("os.environ", env), \
                    patch("deploy.onstate_worker.time.time", return_value=200), \
                    patch("deploy.onstate_worker.time.sleep"), \
                    patch("deploy.onstate_worker.configure_http_requests"), \
                    patch("deploy.onstate_worker.threading.Thread"):
                with self.assertRaisesRegex(OSError, "cleanup failure"):
                    run_onstate(worker)
            worker.flush_and_pause.assert_called_once()


if __name__ == "__main__":
    unittest.main()
