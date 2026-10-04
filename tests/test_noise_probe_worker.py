from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from deploy.noise_probe_worker import VERSION, run_noise_probe, validate_ticket
from deploy.space_worker import Worker
from research.campaign import digest
from tools.linux_noise_probe import contract, PLAN_SHA
from tests.test_inference_worker import admission, fixture
from tests.test_linux_noise_probe import result


def noise_admission():
    ticket, ledger, environment = admission()
    ticket.update(version=VERSION, contract_sha256=digest(contract()), session="noise-probe-fixture-1")
    ledger["batches"][0].update(session=ticket["session"], status="reserved_noise_probe")
    environment.update(RL_SESSION_ID=ticket["session"], RL_MODE="noise_control_probe",
                       RL_CONTEXT_REVISION="b" * 40)
    return ticket, ledger, environment


class NoiseWorkerTests(unittest.TestCase):
    def test_fresh_physics_session_cannot_use_inference_or_training_context(self):
        ticket, ledger, environment = noise_admission()
        self.assertEqual(validate_ticket(ticket, ledger, 200, environment)["reserved_usd"], .005)
        for change in ({"RL_MODE": "inference_probe"}, {"RL_SESSION_ID": "inference-old"},
                       {"RL_DEADLINE_EPOCH": "701"}):
            with self.assertRaises(ValueError):
                validate_ticket(ticket, ledger, 200, {**environment, **change})
        ledger["batches"][0]["verified_end_epoch"] = 300
        with self.assertRaises(ValueError):
            validate_ticket(ticket, ledger, 200, environment)

    def test_route_never_dispatches_old_learning_modes(self):
        worker = Worker.__new__(Worker);worker.mode = "noise_control_probe"
        with patch("deploy.noise_probe_worker.run_noise_probe") as run:
            worker.run();run.assert_called_once_with(worker)

    def test_mocked_probe_requires_explicit_amendment_durable_claim_then_pauses(self):
        ticket, ledger, environment = noise_admission()
        payload = {"ticket": ticket, "ledger": ledger, "provenance": {}, "inputs": {},
                   "transport_amendment": {"version": contract()["version"],
                                         "original_plan_sha256": PLAN_SHA,
                                         "scientific_plan_unchanged": True,
                                         "maximum_reserved_compute_usd": .01,
                                         "maximum_child_seconds": 600}}
        with tempfile.TemporaryDirectory() as directory:
            worker = fixture(directory);worker.mode = "noise_control_probe";worker.session = ticket["session"]
            events = [];worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            def dispatch(args, name, **kwargs):
                events.append(name)
                self.assertEqual(args[1:3], ["-m", "tools.linux_noise_probe"])
                self.assertLessEqual(kwargs["timeout_seconds"], 600)
                self.assertNotIn("HF_TOKEN", kwargs["environment"])
                self.assertNotIn("AGENT_BROWSER_CDP", kwargs["environment"])
                output = worker.artifacts / "noise_probe_result";output.mkdir()
                (output / "report.json").write_text(json.dumps(result()))
            worker.run_command.side_effect = dispatch
            with patch.dict("os.environ", environment), \
                    patch("deploy.noise_probe_worker.time.time", return_value=200), \
                    patch("deploy.noise_probe_worker.time.sleep"), \
                    patch("deploy.noise_probe_worker.threading.Thread"), \
                    patch("deploy.noise_probe_worker.pinned_json", return_value=payload), \
                    patch("deploy.noise_probe_worker.fingerprint", return_value={}), \
                    patch("deploy.noise_probe_worker.PROVENANCE_KEYS", ()), \
                    patch("deploy.noise_probe_worker.restore_inputs", return_value=Path(directory) / "inputs"):
                run_noise_probe(worker)
            self.assertEqual(events, ["sync", "sync", "noise_control_probe"])
            self.assertTrue(any(call.kwargs.get("phase") == "noise_probe_complete"
                                for call in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_terminal_or_interrupted_probe_never_resumes(self):
        ticket, _, environment = noise_admission()
        for phase in ("noise_probe_complete", "noise_probe_stopped", "noise_probe_claimed"):
            with tempfile.TemporaryDirectory() as directory:
                worker = fixture(directory);worker.mode = "noise_control_probe";worker.session = ticket["session"]
                worker.restore_status.return_value = {"phase": phase}
                with patch.dict("os.environ", environment), \
                        patch("deploy.noise_probe_worker.time.time", return_value=200), \
                        patch("deploy.noise_probe_worker.time.sleep"), \
                        patch("deploy.noise_probe_worker.threading.Thread"), \
                        patch("deploy.noise_probe_worker.pinned_json") as load:
                    run_noise_probe(worker)
                load.assert_not_called();worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_missing_amendment_and_failed_sync_prevent_physics(self):
        ticket, ledger, environment = noise_admission()
        with tempfile.TemporaryDirectory() as directory:
            worker = fixture(directory);worker.mode = "noise_control_probe";worker.session = ticket["session"]
            worker.bounded_sync.return_value = False
            payload = {"ticket": ticket, "ledger": ledger, "provenance": {},
                       "transport_amendment": {"version": "wrong"}}
            with patch.dict("os.environ", environment), \
                    patch("deploy.noise_probe_worker.time.time", return_value=200), \
                    patch("deploy.noise_probe_worker.time.sleep"), \
                    patch("deploy.noise_probe_worker.threading.Thread"), \
                    patch("deploy.noise_probe_worker.pinned_json", return_value=payload), \
                    patch("deploy.noise_probe_worker.fingerprint", return_value={}), \
                    patch("deploy.noise_probe_worker.PROVENANCE_KEYS", ()), \
                    patch("deploy.noise_probe_worker.restore_inputs") as restore:
                run_noise_probe(worker)
            restore.assert_not_called();worker.run_command.assert_not_called()
            worker.flush_and_pause.assert_called_once()


if __name__ == "__main__":
    unittest.main()
