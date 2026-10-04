import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from research.campaign import digest
from research.onstate_campaign import DATA_SHA, contract
from research.onstate_execution import (
    ADMISSION_VERSION, PREFLIGHT_CHECKS, RunPermit, child_environment, execute,
    load_trainer_grant, require_permit, validate_admission)
from tests.test_timing_execution import CURRENT, admission_fixture as original_fixture

DATA = {"data_sha256": DATA_SHA, "normalization": {"frozen": True}, "rows": {"total": 5376}}


def admission_fixture(mode="onstate_study"):
    ticket, ledger, environment = original_fixture()
    session = "onstate-synthetic-1"
    ticket.update(version=ADMISSION_VERSION, session=session, contract_sha256=digest(contract()), dataset=DATA)
    ticket["preflight"].update(session=session, checks={name: True for name in PREFLIGHT_CHECKS}, dataset=DATA)
    ledger["batches"][-1]["session"] = session
    environment.update(RL_SESSION_ID=session, RL_MODE=mode)
    return ticket, ledger, environment


class OnStateExecutionTests(unittest.TestCase):
    def test_new_budget_source_preflight_and_data_are_admitted_only_together(self):
        ticket, ledger, environment = admission_fixture()
        self.assertEqual(validate_admission(ticket, ledger, CURRENT, 200, environment)["reserved_maximum_cost"], .03)
        for mutate in (
            lambda t, l, e: t["preflight"]["checks"].update(onstate_smoke_augmented=False),
            lambda t, l, e: t["preflight"].update(dataset={"data_sha256": "wrong"}),
            lambda t, l, e: t.update(paused_before_launch=False),
            lambda t, l, e: l["batches"][-1].update(maximum_estimated_compute_cost=.061),
            lambda t, l, e: e.update(RL_MODE="imitation_study"),
            lambda t, l, e: l["batches"][-1].update(verified_end_epoch=150),
            lambda t, l, e: l.update(operating_ceiling=.1),
        ):
            values = admission_fixture()
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200, values[2])
        with self.assertRaises(ValueError):
            validate_admission(ticket, ledger, CURRENT, 3650, environment)

    def test_desktop_forged_and_old_permits_never_admit_full_work(self):
        ticket, ledger, environment = admission_fixture()
        environment["FACTORY_DESKTOP_CDP_PORT"] = "fixture"
        with patch("research.onstate_execution.fingerprint") as source:
            with self.assertRaisesRegex(ValueError, "remote-only"):
                execute(Path("missing"), Path("missing"), ticket, ledger, environment)
            source.assert_not_called()
        with self.assertRaises(ValueError):
            RunPermit({}, {})
        with self.assertRaisesRegex(ValueError, "validated parent"):
            require_permit({"old_permit": True}, "original_demonstrations", 9)

    def test_children_remove_credentials_and_all_browser_attachments(self):
        clean = child_environment({"HF_TOKEN": "fixture", "AGENT_BROWSER_CDP": "fixture",
                                   "FACTORY_DESKTOP_CDP_PORT": "fixture", "DISPLAY": "fixture",
                                   "RL_MODE": "onstate_study"})
        self.assertEqual(clean, {"RL_MODE": "onstate_study"})

    def grant(self, root):
        ticket, ledger, environment = admission_fixture()
        claim = root / "execution_claim.json"
        claim.write_text('{"owned":"fixture"}')
        dataset = root / "data"
        dataset.mkdir()
        (dataset / "data.npz").write_bytes(b"fixture-data")
        run = contract()["runs"][0]
        output = root / "runs" / run["name"]
        payload = {"version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger, "run": run,
                   "parent_pid": 123, "parent_creation_time": 50,
                   "dataset_dir": str(dataset), "output_dir": str(output), "claim_file": str(claim),
                   "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}
        grant = root / "grant.json"
        grant.write_text(json.dumps(payload))
        environment["RL_ONSTATE_GRANT"] = str(grant)
        args = SimpleNamespace(arm=run["arm"], seed=9, dataset=str(dataset), output_dir=str(output),
                               remote_training=True, smoke=False)
        return environment, args, claim, dataset

    def test_grant_checks_parent_creation_time_paths_claim_and_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            environment, args, claim, dataset = self.grant(Path(folder))
            digest_fixture = hashlib.sha256(b"fixture-data").hexdigest()
            with patch("research.onstate_execution.remote_host", return_value=True), \
                    patch("research.onstate_execution.os.getppid", return_value=123), \
                    patch("research.onstate_execution.psutil.Process", return_value=Mock(create_time=lambda: 50)), \
                    patch("research.onstate_execution.fingerprint", return_value=CURRENT), \
                    patch("research.onstate_execution.time.time", return_value=200), \
                    patch("research.onstate_execution.DATA_SHA", digest_fixture), \
                    patch("research.onstate_execution.validate_admission"):
                permit = load_trainer_grant(args, environment)
                permit.verify(args.arm, 9)
                with self.assertRaisesRegex(ValueError, "arm/seed"):
                    permit.verify(args.arm, 10)
                args.output_dir = str(Path(folder) / "wrong")
                with self.assertRaisesRegex(ValueError, "paths"):
                    load_trainer_grant(args, environment)
                (dataset / "data.npz").write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "archive"):
                    permit.verify(args.arm, 9)
                claim.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError, "claim"):
                    permit.verify(args.arm, 9)

    def test_exclusive_claim_is_durable_and_failure_stops_next_run(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "onstate_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))
            with patch("research.onstate_execution.remote_host", return_value=True), \
                    patch("research.onstate_execution.fingerprint", return_value=CURRENT), \
                    patch("research.onstate_execution.time.time", return_value=200), \
                    patch("research.onstate_execution.time.sleep"), \
                    patch("research.onstate_execution.dataset_contract", return_value=DATA), \
                    patch("research.onstate_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.onstate_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.onstate_execution.run_bounded", side_effect=ValueError("owned fixture")) as run:
                with self.assertRaisesRegex(ValueError, "owned fixture"):
                    execute(root, root / "data", ticket, ledger, environment, durable_claim=lambda: True)
                self.assertEqual(run.call_count, 1)
                with self.assertRaisesRegex(ValueError, "silently resume"):
                    execute(root, root / "data", ticket, ledger, environment, durable_claim=lambda: True)
            self.assertTrue((root / "execution_claim.json").is_file())

    def test_exact_six_sequential_runs_require_durable_claim(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "onstate_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))
            launched = []
            def dispatch(args, name, child):
                output = Path(args[args.index("--output-dir")+1])
                self.assertFalse(output.exists())
                output.mkdir()
                self.assertIn("RL_ONSTATE_GRANT", child)
                self.assertNotIn("HF_TOKEN", child)
                launched.append(name)
            def summary(directory):
                return {"rows": [{"run": name} for name in launched],
                        "missing_runs": [run["name"] for run in contract()["runs"]
                                         if run["name"] not in launched]}
            with patch("research.onstate_execution.remote_host", return_value=True), \
                    patch("research.onstate_execution.fingerprint", return_value=CURRENT), \
                    patch("research.onstate_execution.time.time", return_value=200), \
                    patch("research.onstate_execution.time.sleep"), \
                    patch("research.onstate_execution.dataset_contract", return_value=DATA), \
                    patch("research.onstate_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.onstate_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.onstate_execution.aggregate", side_effect=summary), \
                    patch("research.onstate_execution.goal_projection", return_value={"final_goal_verified": False}):
                result = execute(root, root / "data", ticket, ledger,
                                 {**environment, "HF_TOKEN": "fixture-only"}, dispatch, durable_claim=lambda: True)
            self.assertFalse(result["missing_runs"])
            self.assertEqual(launched, [run["name"] for run in contract()["runs"]])

    def test_undurable_claim_blocks_first_dispatch(self):
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "onstate_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))
            with patch("research.onstate_execution.remote_host", return_value=True), \
                    patch("research.onstate_execution.fingerprint", return_value=CURRENT), \
                    patch("research.onstate_execution.time.time", return_value=200), \
                    patch("research.onstate_execution.time.sleep"), \
                    patch("research.onstate_execution.dataset_contract", return_value=DATA), \
                    patch("research.onstate_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.onstate_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.onstate_execution.run_bounded") as run:
                with self.assertRaisesRegex(ValueError, "durable"):
                    execute(root, root / "data", ticket, ledger, environment, durable_claim=lambda: False)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
