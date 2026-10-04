from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from research.campaign import digest
from research.imitation_campaign import contract
from research.imitation_execution import (
    ADMISSION_VERSION, PREFLIGHT_CHECKS, RunPermit, execute, load_trainer_grant,
    require_permit, validate_admission)
from tests.test_timing_execution import CURRENT, admission_fixture as timing_fixture

DATA = {"data_sha256": "e" * 64, "eligible_samples": 3576,
        "normalization_contract": {"frozen": True}}


def admission_fixture():
    ticket, ledger, environment = timing_fixture()
    session = "imitation-synthetic-1"
    ticket.update(version=ADMISSION_VERSION, session=session, contract_sha256=digest(contract()), dataset=DATA)
    ticket["preflight"].update(session=session, checks={name: True for name in PREFLIGHT_CHECKS}, dataset=DATA)
    ledger["batches"][-1]["session"] = session
    environment["RL_SESSION_ID"] = session
    return ticket, ledger, environment


class ImitationExecutionTests(unittest.TestCase):
    def test_fresh_admission_preserves_common_cost_source_and_preflight_gates(self):
        ticket, ledger, env = admission_fixture()
        result = validate_admission(ticket, ledger, CURRENT, 200.0, env)
        self.assertEqual(result["reserved_maximum_cost"], 0.03)
        self.assertEqual(result["cumulative_reserved_or_elapsed_cost"], 0.13)
        for mutate in (
            lambda t, l, e: t["preflight"]["checks"].update(imitation_smoke_bc=False),
            lambda t, l, e: t["preflight"].update(dataset={"changed": True}),
            lambda t, l, e: t.update(paused_before_launch=False),
            lambda t, l, e: l["batches"][-1].update(verified_end_epoch=150),
            lambda t, l, e: l.update(operating_ceiling=0.1),
        ):
            values = admission_fixture();mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200.0, values[2])

    def test_desktop_and_forged_capabilities_are_refused_before_work(self):
        ticket, ledger, env = admission_fixture()
        env["FACTORY_DESKTOP_CDP_PORT"] = "fixture"
        with patch("research.imitation_execution.fingerprint") as source:
            with self.assertRaisesRegex(ValueError, "remote-only"):
                execute(Path("missing"), Path("missing"), ticket, ledger, env)
            source.assert_not_called()
        with self.assertRaisesRegex(ValueError, "validated grant"):
            RunPermit({}, {})
        with self.assertRaisesRegex(ValueError, "validated parent"):
            require_permit({"fake": True}, "behavior_cloning_only", 6)

    def grant(self, root, ticket, ledger, run):
        claim = root / "execution_claim.json";claim.write_text('{"owned":"fixture"}')
        output = root / "runs" / run["name"];dataset = root / "data"
        grant = root / "grant.json"
        grant.write_text(json.dumps({
            "version": ADMISSION_VERSION, "ticket": ticket, "ledger": ledger, "run": run,
            "output_dir": str(output), "dataset_dir": str(dataset), "parent_pid": 123,
            "claim_file": str(claim), "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}))
        return claim, output, dataset, grant

    def test_parent_grant_binds_seed_paths_corpus_claim_and_deadline(self):
        ticket, ledger, env = admission_fixture();run = contract()["runs"][1]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);claim, output, dataset, grant = self.grant(root, ticket, ledger, run)
            env["RL_IMITATION_GRANT"] = str(grant)
            args = SimpleNamespace(arm=run["arm"], seed=6, dataset=str(dataset), output_dir=str(output),
                                   remote_training=True, smoke=False)
            with patch("research.imitation_execution.remote_host", return_value=True), \
                    patch("research.imitation_execution.os.getppid", return_value=123), \
                    patch("research.imitation_execution.fingerprint", return_value=CURRENT), \
                    patch("research.imitation_execution.time.time", return_value=200.0):
                permit = load_trainer_grant(args, env)
                self.assertEqual(permit.record()["dataset_sha256"], DATA["data_sha256"])
                with self.assertRaisesRegex(ValueError, "corpus"):
                    permit.verify(run["arm"], 6, "wrong")
                args.seed = 7
                with self.assertRaisesRegex(ValueError, "arguments"):
                    load_trainer_grant(args, env)
                args.seed = 6;claim.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError, "claim"):
                    permit.verify(run["arm"], 6)

    def test_exclusive_durable_claim_and_failure_stop_prevent_silent_resume(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);dataset = root / "data"
            (root / "imitation_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))
            with patch("research.imitation_execution.remote_host", return_value=True), \
                    patch("research.imitation_execution.fingerprint", return_value=CURRENT), \
                    patch("research.imitation_execution.time.time", return_value=200.0), \
                    patch("research.imitation_execution.time.sleep"), \
                    patch("research.imitation_execution.dataset_contract", return_value=DATA), \
                    patch("research.imitation_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.imitation_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.imitation_execution.run_bounded", side_effect=ValueError("owned fixture fails")) as run:
                with self.assertRaisesRegex(ValueError, "owned fixture"):
                    execute(root, dataset, ticket, ledger, env, durable_claim=lambda: True)
                self.assertEqual(run.call_count, 1)
                with self.assertRaisesRegex(ValueError, "silently resume"):
                    execute(root, dataset, ticket, ledger, env, durable_claim=lambda: True)
            self.assertTrue((root / "execution_claim.json").is_file())

    def test_undurable_claim_never_dispatches(self):
        ticket, ledger, env = admission_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "imitation_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))
            with patch("research.imitation_execution.remote_host", return_value=True), \
                    patch("research.imitation_execution.fingerprint", return_value=CURRENT), \
                    patch("research.imitation_execution.time.time", return_value=200.0), \
                    patch("research.imitation_execution.time.sleep"), \
                    patch("research.imitation_execution.dataset_contract", return_value=DATA), \
                    patch("research.imitation_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.imitation_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.imitation_execution.run_bounded") as run:
                with self.assertRaisesRegex(ValueError, "durable"):
                    execute(root, root / "data", ticket, ledger, env, durable_claim=lambda: False)
                run.assert_not_called()

    def test_sequential_executor_schedules_only_the_nine_declared_runs(self):
        ticket, ledger, env = admission_fixture();launched = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);dataset = root / "data"
            (root / "imitation_campaign.json").write_text(json.dumps({
                "contract": contract(), "provenance": CURRENT, "dataset": DATA}))

            def dispatch(args, name, child):
                output = Path(args[args.index("--output-dir") + 1])
                self.assertFalse(output.exists())
                output.mkdir()
                self.assertIn("RL_IMITATION_GRANT", child)
                launched.append(name)

            def summary(directory):
                return {"rows": [{"run": name} for name in launched],
                        "missing_runs": [run for run in contract()["runs"] if run["name"] not in launched]}

            with patch("research.imitation_execution.remote_host", return_value=True), \
                    patch("research.imitation_execution.fingerprint", return_value=CURRENT), \
                    patch("research.imitation_execution.time.time", return_value=200.0), \
                    patch("research.imitation_execution.time.sleep"), \
                    patch("research.imitation_execution.dataset_contract", return_value=DATA), \
                    patch("research.imitation_execution.effective_limits", return_value={
                        "logical_cpus": 8, "available_ram_bytes": 32 * 2**30}), \
                    patch("research.imitation_execution.psutil.disk_usage", return_value=Mock(free=20 * 2**30)), \
                    patch("research.imitation_execution.aggregate", side_effect=summary):
                result = execute(root, dataset, ticket, ledger, env, dispatch, durable_claim=lambda: True)
            self.assertEqual(launched, [run["name"] for run in contract()["runs"]])
            self.assertFalse(result["missing_runs"])


if __name__ == "__main__":
    unittest.main()
