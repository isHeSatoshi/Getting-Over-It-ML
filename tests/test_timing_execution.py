from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from research.campaign import digest
from research.timing_campaign import contract
from research.timing_execution import (
    ADMISSION_VERSION, ARTIFACT_REPO, PREFLIGHT_CHECKS, SPACE, child_environment,
    execute, load_trainer_grant, run_bounded, terminate_owned_process, validate_admission,
)


CURRENT = {"project_sha256": "a" * 64, "runtime_sha256": "b" * 64,
           "asset_set_sha256": "c" * 64, "source_sha256": {"fixture": "d" * 64}}


def admission_fixture():
    """Synthetic parent admission, never provider evidence or a real reservation."""
    session, start, deadline = "timing-synthetic-1", 100.0, 3700.0
    preflight = {"phase": "preflight_complete", "session": session,
                 "source_space_revision": "a" * 40, "deadline_epoch": deadline,
                 "campaign_budget_start_epoch": start, "provenance": deepcopy(CURRENT),
                 "checks": {name: True for name in PREFLIGHT_CHECKS}}
    ticket = {"version": ADMISSION_VERSION, "session": session, "space": SPACE,
              "artifact_repo": ARTIFACT_REPO, "contract_sha256": digest(contract()),
              "paused_before_launch": True, "source_space_revision": "a" * 40,
              "runtime_policy": {"hardware": "cpu-upgrade", "sleep_policy": "never", "replicas": 1},
              "start_epoch": start, "deadline_epoch": deadline, "preflight": preflight}
    ledger = {"currency": "USD", "operating_ceiling": 10.0, "batches": [
        {"session": "historical-synthetic", "verified_end_epoch": 90.0,
         "estimated_elapsed_compute_cost_upper_bound": 0.1},
        {"session": session, "space": SPACE, "tier": "cpu-upgrade", "start_epoch": start,
         "deadline_epoch": deadline, "rate_per_hour": 0.03, "maximum_estimated_compute_cost": 0.03,
         "verified_end_epoch": None, "status": "reserved_preflight",
         "source_space_revision": "a" * 40}]}
    environment = {"RL_SESSION_ID": session, "RL_SPACE_ID": SPACE, "RL_ARTIFACT_REPO": ARTIFACT_REPO,
                   "RL_DEADLINE_EPOCH": str(deadline)}
    return ticket, ledger, environment


class TimingExecutionTests(unittest.TestCase):
    def test_valid_synthetic_admission_is_scoped_and_capped(self):
        ticket, ledger, environment = admission_fixture()
        admitted = validate_admission(ticket, ledger, CURRENT, 200.0, environment)
        self.assertEqual(admitted["deadline_epoch"], 3700.0)
        self.assertEqual(admitted["reserved_maximum_cost"], 0.03)
        self.assertEqual(admitted["cumulative_reserved_or_elapsed_cost"], 0.13)

    def test_missing_failed_or_drifted_preflight_cannot_admit(self):
        for mutate in (
            lambda t, l, e: t.update(paused_before_launch=False),
            lambda t, l, e: t["preflight"].update(phase="failed"),
            lambda t, l, e: t["preflight"]["checks"].update(timing_fidelity=False),
            lambda t, l, e: t["preflight"]["checks"].update(timing_fidelity=1),
            lambda t, l, e: t["preflight"].update(source_space_revision="b" * 40),
            lambda t, l, e: t["preflight"]["provenance"].update(project_sha256="wrong"),
            lambda t, l, e: t.update(contract_sha256="wrong"),
            lambda t, l, e: l["batches"][-1].update(source_space_revision="b" * 40),
            lambda t, l, e: t["runtime_policy"].update(replicas=2),
            lambda t, l, e: e.update(RL_SESSION_ID="poc-20261004-v2"),
            lambda t, l, e: e.update(RL_DEADLINE_EPOCH="3701"),
        ):
            values = admission_fixture()
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200.0, values[2])

    def test_expired_unreserved_oversized_and_concurrent_costs_refused(self):
        for mutate in (
            lambda t, l, e: l["batches"][-1].update(verified_end_epoch=150),
            lambda t, l, e: l["batches"][-1].update(status="training_started"),
            lambda t, l, e: l["batches"][-1].update(maximum_estimated_compute_cost=0.01),
            lambda t, l, e: l["batches"][-1].update(deadline_epoch=100 + 17 * 3600),
            lambda t, l, e: l.update(operating_ceiling=0.1),
            lambda t, l, e: l["batches"].append(deepcopy(l["batches"][-1])),
            lambda t, l, e: l["batches"][0].update(verified_end_epoch=None,
                                                 maximum_estimated_compute_cost=0.1),
        ):
            values = admission_fixture()
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200.0, values[2])
        ticket, ledger, environment = admission_fixture()
        for now in (99.0, 3700.0, float("nan")):
            with self.assertRaises(ValueError):
                validate_admission(ticket, ledger, CURRENT, now, environment)

    def test_parent_credential_variables_are_removed_without_printing_values(self):
        values = {"HF_TOKEN": "synthetic", "HUGGING_FACE_HUB_TOKEN": "synthetic",
                  "RL_CONTROL_TOKEN": "synthetic", "OTHER_API_KEY": "synthetic",
                  "other_password": "synthetic", "PATH": "/fixture", "RL_SESSION_ID": "timing-fixture"}
        self.assertEqual(child_environment(values), {"PATH": "/fixture", "RL_SESSION_ID": "timing-fixture"})

    def test_desktop_execution_refused_before_files_or_subprocesses(self):
        ticket, ledger, environment = admission_fixture()
        environment["FACTORY_DESKTOP_CDP_PORT"] = "fixture"
        with patch("research.timing_execution.fingerprint") as source:
            with self.assertRaisesRegex(ValueError, "remote-only"):
                execute(Path("not-present"), ticket, ledger, environment)
            source.assert_not_called()

    def test_existing_claim_or_runs_refuse_silent_resume(self):
        ticket, ledger, environment = admission_fixture()
        for existing in ("execution_claim.json", "runs"):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "timing_campaign.json").write_text(json.dumps({
                    "contract": contract(), "provenance": CURRENT}))
                target = root / existing
                target.mkdir() if existing == "runs" else target.write_text("{}")
                with patch("research.timing_execution.remote_host", return_value=True), \
                        patch("research.timing_execution.fingerprint", return_value=CURRENT), \
                        patch("research.timing_execution.time.time", return_value=200.0), \
                        patch("research.timing_execution.run_bounded") as launch:
                    with self.assertRaisesRegex(ValueError, "silently resume"):
                        execute(root, ticket, ledger, environment)
                    launch.assert_not_called()

    def test_failed_owned_job_stops_before_next_run_and_preserves_claim(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "timing_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT}))
            with patch("research.timing_execution.remote_host", return_value=True), \
                    patch("research.timing_execution.fingerprint", return_value=CURRENT), \
                    patch("research.timing_execution.time.time", return_value=200.0), \
                    patch("research.timing_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.timing_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.timing_execution.run_bounded", side_effect=ValueError("fixture failure")) as launch:
                with self.assertRaisesRegex(ValueError, "fixture failure"):
                    execute(root, ticket, ledger, environment)
                self.assertEqual(launch.call_count, 1)
            self.assertTrue((root / "execution_claim.json").exists())
            self.assertTrue((root / "runs").is_dir())

    def test_deadline_before_spawn_does_not_launch(self):
        with patch("research.timing_execution.remote_host", return_value=True), \
                patch("research.timing_execution.time.time", return_value=200.0), \
                patch("research.timing_execution.subprocess.Popen") as launch:
            with self.assertRaisesRegex(ValueError, "expired"):
                run_bounded([], "unused", {}, 199.0)
            launch.assert_not_called()

    def test_cleanup_time_is_reserved_before_the_paid_deadline(self):
        from research.timing_execution import FINALIZATION_SECONDS
        with patch("research.timing_execution.remote_host", return_value=True), \
                patch("research.timing_execution.time.time", return_value=200.0), \
                patch("research.timing_execution.subprocess.Popen") as launch:
            with self.assertRaisesRegex(ValueError, "cleanup reserve"):
                run_bounded([], "unused", {}, 200.0 + FINALIZATION_SECONDS)
            launch.assert_not_called()

    def test_sequential_executor_finishes_only_six_declared_runs(self):
        ticket, ledger, environment = admission_fixture()
        launched = []
        declared = contract()["runs"]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "timing_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT}))

            def fake_run(args, log, env, deadline):
                self.assertEqual(deadline, ticket["deadline_epoch"])
                output = Path(args[args.index("--output-dir") + 1])
                self.assertFalse(output.exists())
                output.mkdir()  # Owned orchestration fixture; no learner launched.
                launched.append(output.name)

            def fake_aggregate(directory):
                return {"rows": [{"run": name} for name in launched],
                        "missing_runs": [run["name"] for run in declared if run["name"] not in launched]}

            with patch("research.timing_execution.remote_host", return_value=True), \
                    patch("research.timing_execution.fingerprint", return_value=CURRENT), \
                    patch("research.timing_execution.time.time", return_value=200.0), \
                    patch("research.timing_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.timing_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.timing_execution.run_bounded", side_effect=fake_run), \
                    patch("research.timing_execution.aggregate", side_effect=fake_aggregate):
                result = execute(root, ticket, ledger, environment)
            self.assertEqual(launched, [run["name"] for run in declared])
            self.assertFalse(result["missing_runs"])
            self.assertTrue((root / "summary.json").is_file())

    def test_timeout_terminates_only_owned_group(self):
        import subprocess
        process = Mock(pid=123, poll=Mock(return_value=None))
        process.wait.side_effect = [subprocess.TimeoutExpired("fixture", 10), None]
        with patch("research.timing_execution.os.killpg", create=True) as terminate, \
                patch("research.timing_execution.signal.SIGKILL", 9, create=True):
            terminate_owned_process(process)
        self.assertEqual([call.args[0] for call in terminate.call_args_list], [123, 123])

    def test_trainer_grant_binds_direct_parent_declared_run_output_and_claim(self):
        import hashlib
        ticket, ledger, environment = admission_fixture()
        run = contract()["runs"][0]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            claim = root / "execution_claim.json"
            claim.write_text('{"owned":"synthetic"}')
            output = root / "runs" / run["name"]
            grant = root / "grant.json"
            payload = {"version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger,
                       "parent_pid": 123, "run": run, "output_dir": str(output),
                       "claim_file": str(claim), "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}
            grant.write_text(json.dumps(payload))
            environment["RL_TIMING_GRANT"] = str(grant)
            args = SimpleNamespace(algorithm="ppo", action="absolute", frame_skip=1, seed=3,
                                   steps=run["steps"], timing_study=True, remote_training=True,
                                   smoke=False, output_dir=str(output))
            with patch("research.timing_execution.remote_host", return_value=True), \
                    patch("research.timing_execution.os.getppid", return_value=123), \
                    patch("research.timing_execution.fingerprint", return_value=CURRENT), \
                    patch("research.timing_execution.time.time", return_value=200.0):
                self.assertEqual(load_trainer_grant(args, environment)["run"], run["name"])
                args.seed = 4
                with self.assertRaisesRegex(ValueError, "arguments"):
                    load_trainer_grant(args, environment)
                args.seed = 3
                claim.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError, "claim"):
                    load_trainer_grant(args, environment)

    def test_undurable_execution_claim_never_dispatches_a_learner(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "timing_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT}))
            with patch("research.timing_execution.remote_host", return_value=True), \
                    patch("research.timing_execution.fingerprint", return_value=CURRENT), \
                    patch("research.timing_execution.time.time", return_value=200.0), \
                    patch("research.timing_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.timing_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.timing_execution.run_bounded") as launch:
                with self.assertRaisesRegex(ValueError, "durable"):
                    execute(root, ticket, ledger, environment, durable_claim=lambda: False)
                launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
