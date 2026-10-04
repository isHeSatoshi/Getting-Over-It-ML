from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy.inference_worker import (
    VERSION, REPO, SPACE, restore_inputs, run_inference, validate_ticket)
from deploy.space_worker import Worker
from research.campaign import digest
from tools.matched_host_inference import INPUTS, contract, sha, validate_grant


def admission():
    ticket = {"version": VERSION, "contract_sha256": digest(contract()),
              "session": "inference-fixture-1", "space": SPACE, "artifact_repo": REPO,
              "paused_before_launch": True, "source_space_revision": "a" * 40,
              "start_epoch": 100, "deadline_epoch": 700,
              "runtime_policy": {"hardware": "cpu-upgrade", "sleep_policy": "never", "replicas": 1}}
    ledger = {"currency": "USD", "operating_ceiling": 10, "batches": [{
        "session": ticket["session"], "start_epoch": 100, "deadline_epoch": 700,
        "rate_per_hour": .03, "maximum_estimated_compute_cost": .005,
        "verified_end_epoch": None, "status": "reserved_inference", "tier": "cpu-upgrade",
        "space": SPACE, "source_space_revision": "a" * 40}]}
    environment = {"RL_MODE": "inference_probe", "RL_SESSION_ID": ticket["session"],
                   "RL_SPACE_ID": SPACE, "RL_ARTIFACT_REPO": REPO, "RL_DEADLINE_EPOCH": "700"}
    return ticket, ledger, environment


def fixture(root):
    worker = Worker.__new__(Worker)
    worker.mode, worker.session = "inference_probe", "inference-fixture-1"
    worker.space, worker.artifact_repo = SPACE, REPO
    worker.max_hours, worker.deadline = 1, 700
    worker.artifacts, worker.status, worker.stop = Path(root), {}, threading.Event()
    worker.api = Mock()
    worker.api.repo_info.return_value = SimpleNamespace(private=True, sha="a" * 40)
    worker.api.get_space_runtime.return_value = SimpleNamespace(
        hardware="cpu-upgrade", requested_hardware="cpu-upgrade", sleep_time=None,
        raw={"replicas": {"requested": 1}})
    worker.restore_status = Mock(return_value=None)
    for name in ("watchdog", "write_status", "terminate_owned_job", "flush_and_pause"):
        setattr(worker, name, Mock())
    worker.bounded_sync = Mock(return_value=True)
    worker.run_command = Mock()
    return worker


class InferenceWorkerTests(unittest.TestCase):
    def test_fresh_small_budget_and_owned_configuration_required(self):
        ticket, ledger, env = admission()
        self.assertEqual(validate_ticket(ticket, ledger, 200, env)["reserved_usd"], .005)
        for key, value in (("RL_MODE", "imitation_study"), ("RL_DEADLINE_EPOCH", "701"),
                           ("RL_SESSION_ID", "imitation-old")):
            changed = {**env, key: value}
            with self.assertRaises(ValueError):
                validate_ticket(ticket, ledger, 200, changed)
        for key, value in (("deadline_epoch", 1400), ("maximum_estimated_compute_cost", .011),
                           ("verified_end_epoch", 300), ("status", "running")):
            changed = deepcopy(ledger);changed["batches"][0][key] = value
            with self.assertRaises(ValueError):
                validate_ticket(ticket, changed, 200, env)

    def test_other_active_reservation_or_over_ceiling_refused(self):
        ticket, ledger, env = admission()
        second = deepcopy(ledger["batches"][0]);second["session"] = "other"
        ledger["batches"].append(second)
        with self.assertRaises(ValueError):
            validate_ticket(ticket, ledger, 200, env)
        second["verified_end_epoch"] = 99
        second["estimated_elapsed_compute_cost_upper_bound"] = 10
        with self.assertRaises(ValueError):
            validate_ticket(ticket, ledger, 200, env)

    def test_dispatch_routes_only_inference_mode(self):
        worker = Worker.__new__(Worker);worker.mode = "inference_probe"
        with patch("deploy.inference_worker.run_inference") as run:
            worker.run()
            run.assert_called_once_with(worker)

    def test_hf_request_client_is_bounded_without_expiring_pause(self):
        from deploy.inference_worker import configure_http_requests
        with patch("huggingface_hub.set_client_factory") as factory:
            configure_http_requests()
            with factory.call_args.args[0]() as client:
                self.assertEqual(client.timeout.connect, 5)
                self.assertEqual(client.timeout.read, 10)

    def test_child_grant_binds_exact_parent_claim_output_and_source(self):
        import tools.matched_host_inference as tool
        ticket, ledger, env = admission()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);claim = root / "claim.json";claim.write_text("{}")
            grant = root / "grant.json"
            payload = {"ticket": ticket, "ledger": ledger, "parent_pid": 71,
                       "parent_creation_time": 100, "inputs_dir": str(root / "inputs"),
                       "output_dir": str(root / "result"), "claim_file": str(claim),
                       "claim_sha256": sha(claim), "worker_deadline_epoch": 320,
                       "provenance": {}, "tool_sha256": sha(Path(tool.__file__).resolve())}
            grant.write_text(json.dumps(payload));env["RL_INFERENCE_GRANT_SHA"] = sha(grant)
            parent = Mock(pid=71);parent.create_time.return_value = 100
            process = Mock();process.parent.return_value = parent
            with patch.dict("os.environ", env, clear=True), patch("sys.platform", "linux"), \
                    patch("psutil.Process", return_value=process), \
                    patch("tools.matched_host_inference.time.time", return_value=200), \
                    patch("research.provenance.fingerprint", return_value={}), \
                    patch("research.timing_campaign.PROVENANCE_KEYS", ()):
                self.assertEqual(validate_grant(grant, root / "inputs", root / "result")["parent_pid"], 71)
                parent.create_time.return_value = 101
                with self.assertRaises(ValueError):
                    validate_grant(grant, root / "inputs", root / "result")
                parent.create_time.return_value = 100
                claim.write_text('{"changed":true}')
                with self.assertRaises(ValueError):
                    validate_grant(grant, root / "inputs", root / "result")

    def test_metadata_rejected_before_any_binary_download(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = fixture(directory)
            specs = {name: {"size": size, "sha256": digest_value,
                           "revision": "b" * 40 if name.endswith(".npz") else
                           "5df6c20390ca641d8d10a2c62471e7f4142b922e",
                           "path": (f"{worker.session}/operator/inputs/matched_inputs.npz"
                                    if name.endswith(".npz") else
                                    "imitation-20261004-v1/imitation_campaign/runs/behavior_cloning_only_seed_7/" + name)}
                     for name, (size, digest_value) in INPUTS.items()}
            worker.api.repo_info.return_value = SimpleNamespace(private=True, siblings=[])
            with patch("huggingface_hub.hf_hub_download") as download:
                with self.assertRaises(ValueError):
                    restore_inputs(worker, specs)
                download.assert_not_called()

    def test_terminal_and_interrupted_states_cannot_resume(self):
        _, _, env = admission()
        for phase in ("inference_complete", "inference_claimed", "failed"):
            with tempfile.TemporaryDirectory() as directory:
                worker = fixture(directory);worker.restore_status.return_value = {"phase": phase}
                with patch.dict("os.environ", env), patch("deploy.inference_worker.time.time", return_value=200), \
                        patch("deploy.inference_worker.threading.Thread"), \
                        patch("deploy.inference_worker.time.sleep"), \
                        patch("deploy.inference_worker.context") as load:
                    run_inference(worker)
                load.assert_not_called();worker.run_command.assert_not_called()
                worker.flush_and_pause.assert_called_once()

    def test_durable_claim_precedes_single_child_and_zero_training_completion(self):
        ticket, ledger, env = admission()
        with tempfile.TemporaryDirectory() as directory:
            worker = fixture(directory);events = []
            worker.bounded_sync.side_effect = lambda: events.append("sync") or True
            payload = {"ticket": ticket, "ledger": ledger, "provenance": {}, "inputs": {}}
            def dispatch(args, name, **kwargs):
                events.append(name)
                self.assertEqual(args[1:3], ["-m", "tools.matched_host_inference"])
                self.assertNotIn("learn", args)
                self.assertLessEqual(kwargs["timeout_seconds"], 120)
                output = worker.artifacts / "inference_result";output.mkdir()
                (output / "report.json").write_text(json.dumps({
                    "status": "inference_complete_no_goal_promotion", "kind": "remote_matched_host",
                    "actual_inference_presentations": 3600, "controlled_ticks": 0,
                    "reset_ticks": 0, "training_updates": 0}))
            worker.run_command.side_effect = dispatch
            with patch.dict("os.environ", env), patch("deploy.inference_worker.time.time", return_value=200), \
                    patch("deploy.inference_worker.threading.Thread"), patch("deploy.inference_worker.time.sleep"), \
                    patch("deploy.inference_worker.context", return_value=(payload, "b" * 40)), \
                    patch("deploy.inference_worker.fingerprint", return_value={}), \
                    patch("deploy.inference_worker.PROVENANCE_KEYS", ()), \
                    patch("deploy.inference_worker.restore_inputs", return_value=Path(directory) / "inputs"):
                run_inference(worker)
            self.assertEqual(events, ["sync", "sync", "inference_probe"])
            self.assertTrue(any(c.kwargs.get("phase") == "inference_complete"
                                for c in worker.write_status.call_args_list))
            worker.flush_and_pause.assert_called_once()

    def test_failed_durable_admission_cannot_download_or_dispatch(self):
        ticket, ledger, env = admission()
        with tempfile.TemporaryDirectory() as directory:
            worker = fixture(directory);worker.bounded_sync.return_value = False
            with patch.dict("os.environ", env), patch("deploy.inference_worker.time.time", return_value=200), \
                    patch("deploy.inference_worker.threading.Thread"), patch("deploy.inference_worker.time.sleep"), \
                    patch("deploy.inference_worker.context", return_value=(
                        {"ticket": ticket, "ledger": ledger, "provenance": {}, "inputs": {}}, "b" * 40)), \
                    patch("deploy.inference_worker.fingerprint", return_value={}), \
                    patch("deploy.inference_worker.PROVENANCE_KEYS", ()), \
                    patch("deploy.inference_worker.restore_inputs") as restore:
                run_inference(worker)
            restore.assert_not_called();worker.run_command.assert_not_called()
            worker.flush_and_pause.assert_called_once()


if __name__ == "__main__":
    unittest.main()
