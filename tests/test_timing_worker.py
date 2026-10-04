from copy import deepcopy
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.space_worker import Worker
from deploy.timing_worker import pinned_context, preflight_commands, run_timing, validate_context
from research.timing_execution import PREFLIGHT_CHECKS
from test_timing_execution import CURRENT, admission_fixture


def worker_fixture(root, mode="timing_preflight"):
    worker = Worker.__new__(Worker)
    worker.mode = mode
    worker.space = "isHeSatoshi/rl-over-it-poc-20261004"
    worker.artifact_repo = "isHeSatoshi/rl-over-it-research-artifacts"
    worker.session = "timing-synthetic-1"
    worker.max_hours, worker.deadline = 1.0, 3700.0
    worker.artifacts = Path(root)
    worker.stop = threading.Event()
    worker.status = {}
    worker.api = Mock()
    worker.api.repo_info.return_value = SimpleNamespace(sha="a" * 40)
    worker.api.get_space_runtime.return_value = SimpleNamespace(
        hardware="cpu-upgrade", requested_hardware="cpu-upgrade", sleep_time=None,
        raw={"replicas": {"requested": 1, "current": 1}})
    worker.restore_status = Mock(return_value=None)
    worker.watchdog, worker.periodic_sync = Mock(), Mock()
    worker.write_status = Mock()
    worker.run_command = Mock()
    worker.bounded_sync = Mock(return_value=True)
    worker.terminate_owned_job, worker.flush_and_pause = Mock(), Mock()
    return worker


class TimingWorkerTests(unittest.TestCase):
    def test_exact_preflight_checks_are_pipeline_only_and_timing_specific(self):
        with tempfile.TemporaryDirectory() as folder:
            commands = preflight_commands(worker_fixture(folder))
            self.assertEqual(tuple(name for name, _ in commands), PREFLIGHT_CHECKS)
            for name, args in commands:
                self.assertNotIn("--remote-training", args)
                if name.startswith("timing_smoke"):
                    self.assertIn("--smoke", args)
                    self.assertIn("--timing-study", args)

    def test_context_refuses_repeated_preflight_or_stale_source_or_wrong_mode_evidence(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            context = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
            with patch.dict("os.environ", environment), patch("deploy.timing_worker.time.time", return_value=200.0):
                self.assertEqual(validate_context(worker, context, CURRENT, None)["session"], worker.session)
                with self.assertRaisesRegex(ValueError, "overwrite"):
                    validate_context(worker, context, CURRENT, {"phase": "preflight_complete"})
                worker.api.repo_info.return_value = SimpleNamespace(sha="b" * 40)
                with self.assertRaisesRegex(ValueError, "deployed"):
                    validate_context(worker, context, CURRENT, None)
                worker.mode = "timing_study"
                with self.assertRaisesRegex(ValueError, "complete timing preflight"):
                    validate_context(worker, {"ticket": ticket, "ledger": ledger}, CURRENT, None)

    def test_successful_preflight_flushes_before_commands_and_always_pauses(self):
        ticket, ledger, environment = admission_fixture()
        context = {"ticket": {**ticket, "preflight": None}, "ledger": ledger}
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            events = []
            worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            worker.run_command.side_effect = lambda args, name: events.append(name)
            with patch.dict("os.environ", environment), \
                    patch("deploy.timing_worker.time.time", return_value=200.0), \
                    patch("deploy.timing_worker.time.sleep"), \
                    patch("deploy.timing_worker.threading.Thread"), \
                    patch("deploy.timing_worker.pinned_context", return_value=(context, "b" * 40)), \
                    patch("deploy.timing_worker.fingerprint", return_value=CURRENT):
                run_timing(worker)
            self.assertEqual(events, ["sync", *PREFLIGHT_CHECKS])
            self.assertTrue(any(call.kwargs.get("phase") == "preflight_complete"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_interrupted_state_does_not_run_checks_or_jobs_and_pauses(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "timing_study")
            worker.restore_status.return_value = {"phase": "timing_dispatch"}
            with patch.dict("os.environ", environment), \
                    patch("deploy.timing_worker.time.time", return_value=200.0), \
                    patch("deploy.timing_worker.time.sleep"), \
                    patch("deploy.timing_worker.threading.Thread"), \
                    patch("deploy.timing_worker.pinned_context", return_value=({"ticket": ticket, "ledger": ledger}, "b" * 40)):
                run_timing(worker)
            worker.run_command.assert_not_called()
            worker.write_status.assert_called_with(
                phase="interrupted", error="Persisted timing work interrupted; no silent restart")
            worker.flush_and_pause.assert_called_once()

    def test_failed_initial_sync_never_dispatches_and_still_pauses(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            worker.bounded_sync.return_value = False
            with patch.dict("os.environ", environment), \
                    patch("deploy.timing_worker.time.time", return_value=200.0), \
                    patch("deploy.timing_worker.time.sleep"), \
                    patch("deploy.timing_worker.threading.Thread"), \
                    patch("deploy.timing_worker.pinned_context", return_value=(
                        {"ticket": {**ticket, "preflight": None}, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.timing_worker.fingerprint", return_value=CURRENT):
                run_timing(worker)
            worker.run_command.assert_not_called()
            self.assertTrue(any(call.kwargs.get("phase") == "failed"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_completed_or_failed_session_is_preserved_without_relaunch(self):
        ticket, ledger, environment = admission_fixture()
        for phase in ("timing_complete", "failed", "budget_stopped"):
            with tempfile.TemporaryDirectory() as folder:
                worker = worker_fixture(folder, "timing_study")
                previous = {"phase": phase, "session": worker.session}
                worker.restore_status.return_value = previous
                with patch.dict("os.environ", environment), \
                        patch("deploy.timing_worker.time.time", return_value=200.0), \
                        patch("deploy.timing_worker.time.sleep"), \
                        patch("deploy.timing_worker.threading.Thread"), \
                        patch("deploy.timing_worker.pinned_context", return_value=(
                            {"ticket": ticket, "ledger": ledger}, "b" * 40)):
                    run_timing(worker)
                self.assertEqual(worker.status, previous)
                worker.write_status.assert_not_called()
                worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_study_requires_operator_and_durable_preflight_then_durable_dispatch(self):
        ticket, ledger, environment = admission_fixture()
        previous = {**deepcopy(ticket["preflight"]), "study_kind": "timing"}
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder, "timing_study")
            worker.restore_status.return_value = previous
            events = []
            worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            with patch.dict("os.environ", environment), \
                    patch("deploy.timing_worker.time.time", return_value=200.0), \
                    patch("deploy.timing_worker.time.sleep"), \
                    patch("deploy.timing_worker.threading.Thread"), \
                    patch("deploy.timing_worker.pinned_context", return_value=(
                        {"ticket": ticket, "ledger": ledger}, "b" * 40)), \
                    patch("deploy.timing_worker.fingerprint", return_value=CURRENT), \
                    patch("deploy.timing_worker.restore_pilot", return_value=Path(folder) / "prior"), \
                    patch("deploy.timing_worker.prepare"), \
                    patch("deploy.timing_worker.execute", side_effect=lambda *args, **kwargs: events.append("execute")):
                run_timing(worker)
            self.assertEqual(events, ["sync", "sync", "execute"])
            self.assertTrue(any(call.kwargs.get("phase") == "timing_complete"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_private_context_fetch_is_pinned_and_scoped_without_real_network(self):
        with tempfile.TemporaryDirectory() as folder:
            worker = worker_fixture(folder)
            source = Path(folder) / "context.json"
            source.write_text('{"synthetic":true}')
            with patch.dict("os.environ", {"RL_CONTEXT_REVISION": "b" * 40}), \
                    patch("huggingface_hub.hf_hub_download", return_value=str(source)) as read:
                payload, revision = pinned_context(worker)
            self.assertEqual(payload, {"synthetic": True})
            self.assertEqual(revision, "b" * 40)
            self.assertEqual(read.call_args.kwargs["filename"],
                             worker.session + "/operator/timing_context.json")
            self.assertEqual(read.call_args.kwargs["revision"], "b" * 40)


if __name__ == "__main__":
    unittest.main()
