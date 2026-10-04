from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.onstate_campaign import DATA_SHA, aggregate, contract, goal_projection, validate_run
from research.onstate_study import ARMS, VALIDATION_CASES, plan
from research.onstate_train import settings
from tests.test_timing_campaign import PROVENANCE, evaluation_fixture

DATA = {"data_sha256": DATA_SHA, "rows": {"total": 5376}, "normalization": {"frozen": True}}
CAMPAIGN = {"contract": contract(), "provenance": PROVENANCE, "dataset": DATA}


def evaluation():
    records = evaluation_fixture(1, 1800)
    for record, case in zip(records, VALIDATION_CASES):
        record["case"] = json.loads(json.dumps(case.describe()))
        record["seed"] = case.reset_seed
        record["final"]["applied_action"] = PhysicalCaseClock(case).apply(np.zeros((1, 2), np.float32), 0)[0].tolist()
    return records


def fixture(run):
    new = 0 if run["arm"] == ARMS[0] else 128000
    manifest = {
        **deepcopy(PROVENANCE), "version": "onstate-trainer-v1",
        "purpose": "admitted remote on-state comparison",
        "config": {"arm": run["arm"], "seed": run["seed"], "smoke": False, "remote_training": True},
        "settings": settings(False), "dataset": deepcopy(DATA),
        "device": "cpu", "reward_normalization": {
            "enabled": False, "clipping": "disabled", "units": "raw_task_units"},
        "initial_parameters_sha256": "b" * 64, "reward_contract": plan()["reward_contract"],
        "environment_contract": plan()["environment"], "evaluation_contract": contract()["study"]["evaluation"],
        "onstate_admission": {"version": "onstate-execution-admission-v1", "session": "onstate-fixture-1",
                             "run": run["name"], "deadline_epoch": 3700, "source_space_revision": "a" * 40,
                             "dataset_sha256": DATA_SHA},
        "python": "fixture-python", "numpy": "fixture-numpy", "torch": "fixture-torch",
        "stable_baselines3": "fixture-sb3"}
    training = {
        "settings": settings(False), "complete": True, "normalization_unchanged": True,
        "nonactor_parameters_unchanged": True, "saved_reload_exact": True, "torch_threads": 1,
        "rl_transitions": 0, "ppo_optimizer_calls": 0, "training_control_ticks": 0, "training_reset_ticks": 0,
        "initial_parameters_sha256": "b" * 64, "final_parameters_sha256": "c" * 64,
        "cloning": {"version": "ppo-actor-demonstration-warm-start-v1",
                    "purpose": "Admitted remote actor demonstration warm start",
                    "samples": 3576 if run["arm"] == ARMS[0] else 5376, "optimizer_step_calls": 2000,
                    "batch_size": 256, "sample_presentations": 512000, "seed": run["seed"],
                    "rl_transitions": 0, "learning_rate": .001, "ppo_optimizer_state_preserved": True,
                    "mean_squared_action_error_before": .5, "mean_squared_action_error_after": .1,
                    "wall_seconds": 1.0, "onstate_sampling": {
                        "arm": run["arm"], "original_presentations": 512000-new,
                        "logged_success_presentations": new, "data_sha256": DATA_SHA}}}
    result = {"evaluation_backend": "reference", "checkpoints": ["untrained", "after_cloning"],
              "untrained": evaluation(), "after_cloning": evaluation()}
    return manifest, training, result


class OnStateCampaignTests(unittest.TestCase):
    def test_synthetic_results_validate_work_fresh_cases_and_zero_completion(self):
        for run in contract()["runs"]:
            row = validate_run(*fixture(run), run, CAMPAIGN)
            self.assertEqual(row["after"]["cases"], 9)
            self.assertEqual(row["after"]["deaths"], 9)
            self.assertEqual(row["after"]["full_completions"], 0)
            self.assertEqual(row["cloning_work"]["sample_presentations"], 512000)

    def test_smoke_mixed_data_wrong_weights_ppo_and_old_cases_fail(self):
        run = contract()["runs"][1]
        for mutate in (
            lambda m, t, e: m["config"].update(smoke=True),
            lambda m, t, e: m["dataset"].update(data_sha256="wrong"),
            lambda m, t, e: t.update(ppo_optimizer_calls=1),
            lambda m, t, e: t.update(torch_threads=True),
            lambda m, t, e: t["cloning"]["onstate_sampling"].update(logged_success_presentations=1),
            lambda m, t, e: e.update(after_cloning=evaluation_fixture(1, 1800)),
            lambda m, t, e: m["onstate_admission"].update(session="imitation-old-1"),
            lambda m, t, e: t.update(normalization_unchanged=False),
        ):
            values = fixture(run)
            mutate(*values)
            with self.assertRaises(ValueError):
                validate_run(*values, run, CAMPAIGN)

    def test_complete_cohorts_still_cannot_verify_final_goal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "onstate_campaign.json").write_text(json.dumps(CAMPAIGN))
            for run in contract()["runs"]:
                output = root / "runs" / run["name"]
                output.mkdir(parents=True)
                for name, value in zip(("manifest.json", "training_summary.json", "evaluation.json"), fixture(run)):
                    (output / name).write_text(json.dumps(value))
            summary = aggregate(root)
            self.assertFalse(summary["missing_runs"])
            self.assertTrue(all(row["complete"] for row in summary["cohorts"]))
            self.assertFalse(summary["final_goal_verified"])
            goal = goal_projection(summary)
            self.assertEqual(goal["worst_seed_reference_completion_rate"], 0)
            self.assertFalse(goal["candidate_goal_passed"])
            self.assertFalse(goal["final_goal_verified"])
            path = root / "runs" / contract()["runs"][1]["name"] / "training_summary.json"
            changed = json.loads(path.read_text())
            changed["initial_parameters_sha256"] = "d" * 64
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                aggregate(root)


if __name__ == "__main__":
    unittest.main()
