from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.goal_worker import commands, run_goal, validate_context
from deploy.space_worker import Worker
from research.campaign import digest
from research.goal_execution import CHECKS, VERSION, GoalPermit, validate_admission
from research.goal_study import plan
from research.phase_controller import SOURCE_DATA_SHA
from tests.test_timing_execution import CURRENT, admission_fixture as old_fixture


def admission_fixture(preflight=False):
    ticket, ledger, environment = old_fixture()
    session = "goal-synthetic-1"
    ticket.update(version=VERSION, session=session, contract_sha256=digest(plan()),
                  prior_data_sha256=SOURCE_DATA_SHA, context_revision="b"*40)
    ticket["preflight"].update(session=session, checks={name: True for name in CHECKS},
                              prior_data_sha256=SOURCE_DATA_SHA)
    ledger["batches"][-1]["session"] = session
    environment.update(RL_MODE="goal_preflight" if preflight else "goal_study",
                       RL_SESSION_ID=session, RL_CONTEXT_REVISION="b"*40)
    return ticket, ledger, environment


def fixture(folder, preflight=True):
    ticket, ledger, environment = admission_fixture(preflight)
    worker = Worker.__new__(Worker)
    worker.mode, worker.session = environment["RL_MODE"], ticket["session"]
    worker.space, worker.artifact_repo = ticket["space"], ticket["artifact_repo"]
    worker.deadline, worker.max_hours = 3700., 1.
    worker.artifacts, worker.state_path = Path(folder), Path(folder)/"status.json"
    worker.state_path.write_text("{}")
    worker.stop, worker.status = threading.Event(), {}
    worker.api = Mock()
    worker.api.repo_info.return_value = SimpleNamespace(private=True, sha="a"*40)
    worker.api.get_space_runtime.return_value = SimpleNamespace(hardware="cpu-upgrade",
        requested_hardware="cpu-upgrade", sleep_time=None, raw={"replicas": {"requested": 1, "current": 1}})
    worker.restore_status = Mock(return_value=None)
    worker.watchdog, worker.write_status, worker.run_command = Mock(), Mock(), Mock()
    worker.terminate_owned_job, worker.flush_and_pause = Mock(), Mock()
    previous = {**deepcopy(ticket["preflight"]), "study_kind": "goal", "operator_context_revision": "c"*40,
                "preflight_physics_ticks": 8000}
    if preflight:
        ticket["preflight"] = None
    context = {"ticket": ticket, "ledger": ledger, "plan": plan(),
               "prior": {"session": worker.session}, "preflight_context_revision": "c"*40}
    return worker, context, environment, previous


class GoalWorkerTests(unittest.TestCase):
    def test_budget_session_runtime_prior_and_passed_gate_required(self):
        ticket, ledger, environment = admission_fixture()
        self.assertEqual(validate_admission(ticket, ledger, CURRENT, 200, environment)["reserved_maximum_cost"], .03)
        for mutate in (
            lambda t, l, e: t["preflight"]["checks"].update(goal_prefix_fidelity=False),
            lambda t, l, e: e.update(RL_MODE="residual_study"),
            lambda t, l, e: t.update(prior_data_sha256="wrong"),
            lambda t, l, e: l.update(operating_ceiling=.01),
            lambda t, l, e: l["batches"][-1].update(verified_end_epoch=150),
        ):
            values = admission_fixture()
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200, values[2])

    def test_forged_permit_is_rejected(self):
        with self.assertRaises(ValueError):
            GoalPermit({}, {})

    def test_preflight_has_no_full_training_and_no_two_simulator_resource_command(self):
        with tempfile.TemporaryDirectory() as folder:
            worker, _, _, _ = fixture(folder)
            checks = commands(worker, Path(folder)/"prior")
            self.assertEqual(tuple(name for name, _ in checks), CHECKS)
            self.assertTrue(all("--remote-training" not in args for _, args in checks))
            self.assertTrue(all("research.resources" not in args for _, args in checks))

    def test_actual_revision_and_missing_preflight_context_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            worker, context, environment, previous = fixture(folder, False)
            with patch.dict("os.environ", environment), patch("deploy.goal_worker.time.time", return_value=200):
                self.assertEqual(validate_context(worker, context, "b"*40, CURRENT, previous)["session"], worker.session)
                with self.assertRaisesRegex(ValueError, "passed"):
                    validate_context(worker, context, "b"*40, CURRENT, None)
                worker.api.repo_info.return_value.sha = "f"*40
                with self.assertRaisesRegex(ValueError, "source"):
                    validate_context(worker, context, "b"*40, CURRENT, previous)

    def run_mock(self, worker, context, environment):
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.dict("os.environ", environment))
            stack.enter_context(patch("deploy.goal_worker.remote_host", return_value=True))
            stack.enter_context(patch("deploy.goal_worker.time.time", return_value=200))
            stack.enter_context(patch("deploy.goal_worker.time.sleep"))
            stack.enter_context(patch("deploy.goal_worker.configure_http_requests"))
            stack.enter_context(patch("deploy.goal_worker.threading.Thread"))
            stack.enter_context(patch("deploy.goal_worker.pinned_context", return_value=(context, "b"*40)))
            stack.enter_context(patch("deploy.goal_worker.fingerprint", return_value=CURRENT))
            stack.enter_context(patch("deploy.goal_worker.stable_backup", return_value=True))
            stack.enter_context(patch("deploy.goal_worker.restore_prior", return_value=worker.artifacts/"prior"))
            stack.enter_context(patch("deploy.goal_worker.effective_limits", return_value={
                "logical_cpus": 8, "available_ram_bytes": 32*2**30}))
            stack.enter_context(patch("deploy.goal_worker.psutil.disk_usage", return_value=SimpleNamespace(free=20*2**30)))
            run_goal(worker)

    def test_interrupted_or_complete_sessions_never_run_again(self):
        for phase in ("goal_seed21", "failed", "goal_complete"):
            with tempfile.TemporaryDirectory() as folder:
                worker, context, environment, _ = fixture(folder, False)
                worker.restore_status.return_value = {"phase": phase}
                self.run_mock(worker, context, environment)
                worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_first_failed_preflight_never_marks_passed_and_always_pauses(self):
        with tempfile.TemporaryDirectory() as folder:
            worker, context, environment, _ = fixture(folder)
            worker.run_command.side_effect = ValueError("mock check failed")
            self.run_mock(worker, context, environment)
            self.assertEqual(worker.run_command.call_count, 1)
            self.assertFalse(any(call.kwargs.get("phase") == "preflight_complete"
                                 for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_cleanup_error_cannot_skip_pause(self):
        with tempfile.TemporaryDirectory() as folder:
            worker, context, environment, _ = fixture(folder)
            worker.restore_status.return_value = {"phase": "failed"}
            worker.terminate_owned_job.side_effect = OSError("cleanup")
            with self.assertRaises(OSError):
                self.run_mock(worker, context, environment)
            worker.flush_and_pause.assert_called_once()

    def test_dispatch_goes_to_goal_not_residual(self):
        worker = Worker.__new__(Worker)
        worker.mode = "goal_study"
        with patch("deploy.goal_worker.run_goal") as run:
            worker.run()
            run.assert_called_once_with(worker)


if __name__ == "__main__":
    unittest.main()
