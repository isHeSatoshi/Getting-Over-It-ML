from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from research.campaign import digest
from research.phase_controller import SOURCE_DATA_SHA
from research.residual_env import ResidualGettingOverItEnv
from research.residual_execution import (PREFLIGHT_CHECKS, VERSION, RunPermit, execute,
                                         require_permit, validate_admission, child_environment,
                                         load_trainer_grant)
from research.residual_study import MAX_RESETS, SEEDS, TRANSITIONS, plan
from research.residual_train import BoundedPhysicalWork, initialize, learn, settings
from tests.test_residual_env import MockRawEnv, fixture
from tests.test_timing_execution import CURRENT, admission_fixture as original_fixture


def admission_fixture():
    ticket, ledger, environment = original_fixture()
    session = "residual-synthetic-1"
    ticket.update(version=VERSION, session=session, contract_sha256=digest(plan()),
                  prior_data_sha256=SOURCE_DATA_SHA, context_revision="b"*40)
    ticket["preflight"].update(session=session, checks={key: True for key in PREFLIGHT_CHECKS},
                              prior_data_sha256=SOURCE_DATA_SHA)
    ledger["batches"][-1]["session"] = session
    environment.update(RL_MODE="residual_study", RL_SESSION_ID=session, RL_CONTEXT_REVISION="b"*40)
    return ticket, ledger, environment


class ResidualResearchTests(unittest.TestCase):
    def test_plan_json_roundtrip_fixed_seeds_work_and_goal_not_verified(self):
        record = plan()
        self.assertEqual(record, json.loads(json.dumps(record)))
        self.assertEqual(record["training_seeds"], [12, 13, 14])
        self.assertEqual(len(record["evaluation"]["cases"]), 9)
        self.assertEqual(record["ppo"]["n_steps"], 1024)
        self.assertEqual(TRANSITIONS, 131072)
        self.assertEqual(record["budget"]["maximum_total_physics_ticks"], 590136)
        self.assertFalse(record["comparison"]["final_goal_verified_from_this_study"])
        self.assertFalse(record["comparison"]["baseline_holds_are_learning"])

    def test_new_parent_budget_preflight_prior_context_all_required(self):
        ticket, ledger, environment = admission_fixture()
        admitted = validate_admission(ticket, ledger, CURRENT, 200, environment)
        self.assertEqual(admitted["reserved_maximum_cost"], .03)
        for mutate in (
            lambda t, l, e: t["preflight"]["checks"].update(residual_zero_fidelity=False),
            lambda t, l, e: t["preflight"]["checks"].update(residual_optimizer_smoke=1),
            lambda t, l, e: t["preflight"].update(prior_data_sha256="changed"),
            lambda t, l, e: t.update(paused_before_launch=False),
            lambda t, l, e: e.update(RL_CONTEXT_REVISION="wrong"),
            lambda t, l, e: e.update(RL_MODE="onstate_study"),
            lambda t, l, e: l["batches"][-1].update(maximum_estimated_compute_cost=.061),
            lambda t, l, e: l["batches"][-1].update(verified_end_epoch=150),
            lambda t, l, e: l.update(operating_ceiling=.1),
        ):
            values = admission_fixture()
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_admission(values[0], values[1], CURRENT, 200, values[2])
        with self.assertRaises(ValueError):
            validate_admission(ticket, ledger, CURRENT, 3650, environment)

    def test_forged_old_or_desktop_permits_never_train(self):
        with self.assertRaises(ValueError):
            RunPermit({}, {})
        with self.assertRaisesRegex(ValueError, "validated"):
            require_permit({"old": True}, 12)
        ticket, ledger, environment = admission_fixture()
        # Simulate a Factory desktop session explicitly so the platform guard is
        # exercised on any host, not only when the tests run on Windows.
        desktop = {**environment, "FACTORY_DESKTOP_CDP_PORT": "1"}
        with self.assertRaisesRegex(ValueError, "Linux"):
            execute(Path("missing"), Path("missing"), ticket, ledger, environment=desktop,
                    durable_claim=lambda: True, durable_run=lambda _: True, auto_pause=lambda: True)

    def test_children_remove_credentials_and_user_browser_sessions(self):
        self.assertEqual(child_environment({"HF_TOKEN": "fixture", "AGENT_BROWSER_CDP": "fixture",
                                           "RL_MODE": "residual_study", "DISPLAY": "fixture"}),
                         {"RL_MODE": "residual_study"})

    def test_mock_optimizer_smoke_counts_only_eight_mock_steps_and_two_updates(self):
        raw = MockRawEnv()
        raw.pipeline_mock_only = True
        adapter = ResidualGettingOverItEnv(raw, *fixture())
        model, vector, physical = initialize(adapter, 12, mock_smoke=True)
        result = learn(model, vector, physical, 12, mock_smoke=True)
        self.assertEqual(result["transitions"], 8)
        self.assertEqual(result["optimizer"]["total_optimizer_step_calls"], 2)
        self.assertEqual(result["physical"]["controlled_physics_ticks"], 8)
        self.assertEqual(result["physical"]["reset_settling_physics_ticks"], 120)
        self.assertTrue(result["mock_smoke"])
        vector.close()

    def test_local_original_game_or_unadmitted_full_learning_rejected_before_learn(self):
        adapter = ResidualGettingOverItEnv(MockRawEnv(), *fixture())
        model, vector, physical = initialize(adapter, 12, mock_smoke=True)
        with patch.object(model, "learn") as call:
            with self.assertRaisesRegex(ValueError, "ONLY"):
                learn(model, vector, physical, 12, mock_smoke=True)
            with self.assertRaisesRegex(ValueError, "permit"):
                learn(model, vector, physical, 12, mock_smoke=False)
            call.assert_not_called()
        vector.close()

    def test_freshness_settings_and_resume_fail_before_optimizer(self):
        raw = MockRawEnv()
        raw.pipeline_mock_only = True
        model, vector, physical = initialize(ResidualGettingOverItEnv(raw, *fixture()), 12, mock_smoke=True)
        model.num_timesteps = 1
        with self.assertRaisesRegex(ValueError, "fresh"):
            learn(model, vector, physical, 12, mock_smoke=True)
        model.num_timesteps = 0
        model.n_epochs = 2
        with self.assertRaisesRegex(ValueError, "settings"):
            learn(model, vector, physical, 12, mock_smoke=True)
        vector.close()

    def test_physical_reset_and_control_caps_fail_before_actual_work(self):
        raw = MockRawEnv()
        adapter = ResidualGettingOverItEnv(raw, *fixture())
        physical = BoundedPhysicalWork(adapter, decisions=1, resets=1)
        physical.reset()
        physical.step(np.zeros(2, np.float32))
        with patch.object(adapter, "step") as step:
            with self.assertRaisesRegex(ValueError, "transition budget"):
                physical.step(np.zeros(2, np.float32))
            step.assert_not_called()
        with patch.object(adapter, "reset") as reset:
            with self.assertRaisesRegex(ValueError, "reset budget"):
                physical.reset()
            reset.assert_not_called()

    def execution_context(self, root):
        (root/"residual_campaign.json").write_text(json.dumps({"plan": plan(), "provenance": CURRENT}))
        return (
            patch("research.residual_execution.remote_host", return_value=True),
            patch("research.residual_execution.fingerprint", return_value=CURRENT),
            patch("research.residual_execution.time.time", return_value=200),
            patch("research.residual_execution.effective_limits", return_value={
                "logical_cpus": 8, "available_ram_bytes": 32*2**30}),
            patch("research.residual_execution.psutil.disk_usage", return_value=Mock(free=20*2**30)),
        )

    def test_undurable_claim_blocks_dispatch_and_pauses_owned_space(self):
        from contextlib import ExitStack
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for guard in self.execution_context(root):
                stack.enter_context(guard)
            dispatch, pause = Mock(), Mock(return_value=True)
            with self.assertRaisesRegex(ValueError, "durable"):
                execute(root, root/"prior", ticket, ledger, environment=environment,
                        durable_claim=lambda: False, durable_run=lambda _: True,
                        auto_pause=pause, dispatch=dispatch)
            dispatch.assert_not_called()
            pause.assert_called_once()
            self.assertTrue((root/"execution_claim.json").exists())

    def test_three_sequential_dispatches_validate_backup_then_pause(self):
        from contextlib import ExitStack
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for guard in self.execution_context(root):
                stack.enter_context(guard)
            stack.enter_context(patch("research.residual_campaign.validate_directory", return_value={}))
            stack.enter_context(patch("research.residual_campaign.aggregate", return_value={"complete": True}))
            dispatched, backed = [], []
            def dispatch(command, seed, child):
                self.assertNotIn("HF_TOKEN", child)
                self.assertIn("RL_RESIDUAL_GRANT", child)
                dispatched.append(seed)
            pause = Mock(return_value=True)
            result = execute(root, root/"prior", ticket, ledger,
                environment={**environment, "HF_TOKEN": "fixture"}, durable_claim=lambda: True,
                durable_run=lambda seed: backed.append(seed) or True, auto_pause=pause, dispatch=dispatch)
            self.assertEqual(dispatched, [12, 13, 14])
            self.assertEqual(backed, [12, 13, 14, "summary"])
            self.assertTrue(result["complete"])
            pause.assert_called_once()
            with self.assertRaisesRegex(ValueError, "resume"):
                execute(root, root/"prior", ticket, ledger, environment=environment,
                        durable_claim=lambda: True, durable_run=lambda _: True, auto_pause=pause)

    def test_first_dispatch_failure_stops_remaining_seeds_and_pauses(self):
        from contextlib import ExitStack
        ticket, ledger, environment = admission_fixture()
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for guard in self.execution_context(root):
                stack.enter_context(guard)
            dispatch, pause = Mock(side_effect=ValueError("fixture failure")), Mock(return_value=True)
            with self.assertRaisesRegex(ValueError, "fixture failure"):
                execute(root, root/"prior", ticket, ledger, environment=environment,
                        durable_claim=lambda: True, durable_run=lambda _: True,
                        auto_pause=pause, dispatch=dispatch)
            dispatch.assert_called_once()
            pause.assert_called_once()

    def test_plan_and_settings_copies_cannot_mutate_contract(self):
        first = plan()
        first["training_seeds"][0] = 99
        self.assertEqual(plan()["training_seeds"], [12, 13, 14])
        ppo = settings(True)
        ppo["batch_size"] = 99
        self.assertEqual(settings(True)["batch_size"], 4)
        self.assertEqual(MAX_RESETS, 257)

    def test_grant_loader_binds_live_parent_output_prior_and_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ticket, ledger, environment = admission_fixture()
            prior, claim = root/"prior", root/"execution_claim.json"
            prior.mkdir()
            archive = prior/"data.npz"
            archive.write_bytes(b"owned mock prior")
            claim.write_text('{"fixture":"claimed"}')
            payload = {"version": VERSION, "ticket": ticket, "ledger": ledger, "seed": 12,
                       "output_dir": str(root/"runs"/"seed12"), "prior_directory": str(prior),
                       "parent_pid": 123, "parent_creation_time": 50, "claim_file": str(claim),
                       "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest()}
            grant = root/"grant.json"
            grant.write_text(json.dumps(payload))
            environment["RL_RESIDUAL_GRANT"] = str(grant)
            args = SimpleNamespace(seed=12, remote_training=True, mock_smoke=False,
                                   output_dir=payload["output_dir"], prior=str(prior))
            with patch("research.residual_execution.remote_host", return_value=True), \
                    patch("research.residual_execution.validate_admission"), \
                    patch("research.residual_execution.fingerprint", return_value=CURRENT), \
                    patch("research.residual_execution.time.time", return_value=200), \
                    patch("research.residual_execution.os.getppid", return_value=123), \
                    patch("research.residual_execution.psutil.Process", return_value=Mock(create_time=lambda: 50)), \
                    patch("research.residual_execution.SOURCE_DATA_SHA",
                          hashlib.sha256(archive.read_bytes()).hexdigest()):
                permit = load_trainer_grant(args, environment)
                permit.verify(12)
                self.assertEqual(permit.record()["session"], "residual-synthetic-1")
                with self.assertRaises(ValueError):
                    permit.verify(13)
                args.output_dir = str(root/"wrong")
                with self.assertRaisesRegex(ValueError, "paths"):
                    load_trainer_grant(args, environment)
                args.output_dir = payload["output_dir"]
                archive.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "archive"):
                    load_trainer_grant(args, environment)
                claim.write_text('{"changed":true}')
                with self.assertRaisesRegex(ValueError, "claim"):
                    permit.verify(12)


if __name__ == "__main__":
    unittest.main()
