from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from research.imitation_campaign import aggregate, command, contract, dataset_contract, prepare, validate_run
from research.imitation_train import settings
from research.reward import RewardConfig
from tests.test_timing_campaign import PROVENANCE, evaluation_fixture


DATASET = {"data_sha256": "e" * 64, "eligible_samples": 3576,
           "normalization_contract": {
               "source": "Eligible training demonstrations only", "samples": 3576,
               "raw_observations_sha256": "f" * 64, "frozen": True, "clip_obs": 10.0, "epsilon": 1e-8}}
CAMPAIGN = {"contract": contract(), "provenance": PROVENANCE, "dataset": DATASET}


def fixture(run):
    """Synthetic orchestration-only evidence, never a real-game success claim."""
    cfg = settings(run["arm"], False)
    manifest = {**deepcopy(PROVENANCE), "version": cfg["version"],
                "purpose": "remote imitation research run", "device": "cpu",
                "config": {"arm": run["arm"], "seed": run["seed"], "smoke": False, "remote_training": True},
                "settings": cfg, "dataset_sha256": DATASET["data_sha256"],
                "normalization_contract": deepcopy(DATASET["normalization_contract"]),
                "reward_contract": RewardConfig().describe(1),
                "reward_normalization": {"enabled": False, "clipping": "disabled", "units": "raw_task_units"},
                "environment_contract": {"action_mode": "absolute", "terrain": True, "frame_skip": 1,
                                         "physics_hz": 30.0, "ordinary_start": True, "privileged_resets": False},
                "evaluation_contract": {
                    "cases": contract()["study"]["evaluation"]["cases"],
                    "benchmarks": contract()["study"]["evaluation"]["benchmarks"]},
                "python": "fixture-python", "numpy": "fixture-numpy", "torch": "fixture-torch",
                "stable_baselines3": "fixture-sb3",
                "imitation_admission": {
                    "version": "imitation-execution-admission-v1", "session": "imitation-fixture-v1",
                    "run": run["name"], "deadline_epoch": 3700.0, "source_space_revision": "a" * 40,
                    "dataset_sha256": DATASET["data_sha256"]}}
    steps = cfg["rl_transitions"]
    resets = steps // cfg["episode_decisions"] + 1 if steps else 0
    cloning = None
    if cfg["cloning_updates"]:
        cloning = {"version": "ppo-actor-demonstration-warm-start-v1",
                   "purpose": "Admitted remote actor demonstration warm start",
                   "samples": 3576, "optimizer_step_calls": 2000, "batch_size": 256,
                   "sample_presentations": 512000, "learning_rate": 0.001, "seed": run["seed"],
                   "rl_transitions": 0, "ppo_optimizer_state_preserved": True,
                   "mean_squared_action_error_before": 0.5, "mean_squared_action_error_after": 0.2,
                   "wall_seconds": 1.0}
    training = {"complete": True, "settings": cfg, "normalization_unchanged": True,
                "torch_threads": 1, "learner_gamma": cfg["gamma"], "learner_gae_lambda": cfg["gae_lambda"],
                "cloning": cloning, "rl_transitions": steps, "learning_wall_seconds": 5.0 if steps else 0.0,
                "optimizer_work": {"version": "optimizer-step-calls-v1", "algorithm": "ppo",
                                   "optimizer_step_calls": {"policy": 3840 if steps else 0},
                                   "total_optimizer_step_calls": 3840 if steps else 0,
                                   "sb3_internal_update_counter": 480 if steps else 0},
                "physical_work": {"version": "controlled-reset-ticks-v1",
                    "scope": "Training environment only; excludes preflight, evaluation and runtime boot",
                    "frame_skip": 1, "decision_steps": steps, "nominal_controlled_physics_ticks": steps,
                    "controlled_physics_ticks": steps, "terminal_short_decisions": 0,
                    "resets": resets, "reset_settling_physics_ticks": resets * 120,
                    "total_counted_physics_ticks": steps + resets * 120}}
    evaluation = {"training_backend": "fast", "evaluation_backend": "reference",
                  "untrained": evaluation_fixture(1, 1800),
                  "after_cloning": evaluation_fixture(1, 1800) if cloning else None,
                  "final": evaluation_fixture(1, 1800)}
    return manifest, training, evaluation


class ImitationCampaignTests(unittest.TestCase):
    def test_nine_sequential_declared_runs_and_commands_do_not_execute(self):
        self.assertEqual(len(contract()["runs"]), 9)
        self.assertEqual([r["seed"] for r in contract()["runs"]], [6] * 3 + [7] * 3 + [8] * 3)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);run = contract()["runs"][0]
            argv = command(run, root / "output", root / "data")
            self.assertIn("--remote-training", argv)
            self.assertFalse((root / "output").exists())
            with self.assertRaises(ValueError):
                command(run, Path("relative"), root / "data")

    def test_full_synthetic_arms_count_cloning_and_rl_separately(self):
        for run in contract()["runs"]:
            result = validate_run(*fixture(run), run, CAMPAIGN)
            self.assertEqual(result["after"]["full_completions"], 0)
            self.assertEqual(result["after"]["deaths"], 9)
            self.assertEqual(result["training_physical_work"]["controlled_physics_ticks"],
                             0 if run["arm"] == "behavior_cloning_only" else 393216)

    def test_smokes_source_dataset_normalization_and_admission_drift_are_refused(self):
        run = contract()["runs"][2]
        for mutate in (
            lambda m, t, e: m["config"].update(smoke=True),
            lambda m, t, e: m.update(purpose="Pipeline-only three-arm smoke"),
            lambda m, t, e: m.update(dataset_sha256="different"),
            lambda m, t, e: m["normalization_contract"].update(frozen=False),
            lambda m, t, e: m["imitation_admission"].update(session="timing-old"),
            lambda m, t, e: m["imitation_admission"].update(dataset_sha256="different"),
            lambda m, t, e: m.update(runtime_sha256="different"),
            lambda m, t, e: m["reward_contract"].update(gamma=0.9),
            lambda m, t, e: m["environment_contract"].update(privileged_resets=True),
            lambda m, t, e: t.update(learner_gae_lambda=0.95),
            lambda m, t, e: t.update(normalization_unchanged=False),
            lambda m, t, e: e.update(evaluation_backend="fast"),
        ):
            values = fixture(run);mutate(*values)
            with self.assertRaises(ValueError):
                validate_run(*values, run, CAMPAIGN)

    def test_incorrect_clone_optimizer_or_reset_work_is_refused(self):
        run = contract()["runs"][2]
        for mutate in (
            lambda t: t["cloning"].update(optimizer_step_calls=8),
            lambda t: t["cloning"].update(sample_presentations=128),
            lambda t: t["cloning"].update(samples=5400),
            lambda t: t["cloning"].update(seed=7),
            lambda t: t["optimizer_work"].update(total_optimizer_step_calls=480),
            lambda t: t["physical_work"].update(reset_settling_physics_ticks=0),
            lambda t: t["physical_work"].update(controlled_physics_ticks=393215),
            lambda t: t["physical_work"].update(terminal_short_decisions=1),
        ):
            manifest, training, evaluation = fixture(run);mutate(training)
            with self.assertRaises(ValueError):
                validate_run(manifest, training, evaluation, run, CAMPAIGN)

    def test_bc_only_cannot_hide_rl_or_changed_final_checkpoint(self):
        run = contract()["runs"][1]
        values = fixture(run);values[1]["rl_transitions"] = 1
        with self.assertRaises(ValueError):
            validate_run(*values, run, CAMPAIGN)
        manifest, training, evaluation = fixture(run)
        evaluation["final"][0]["trace"][0]["body_hit_frames"] = 1
        with self.assertRaisesRegex(ValueError, "BC-only final"):
            validate_run(manifest, training, evaluation, run, CAMPAIGN)

    def write_campaign(self, root, all_runs=True):
        (root / "imitation_campaign.json").write_text(json.dumps(CAMPAIGN))
        for run in contract()["runs"] if all_runs else contract()["runs"][:1]:
            path = root / "runs" / run["name"];path.mkdir(parents=True)
            for name, value in zip(("manifest.json", "training_summary.json", "evaluation.json"), fixture(run)):
                (path / name).write_text(json.dumps(value))

    def test_missing_companions_are_incomplete_and_full_matrix_never_verifies_goal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);self.write_campaign(root, False)
            result = aggregate(root)
            self.assertEqual(len(result["missing_runs"]), 8)
            self.assertFalse(any(c["complete"] for c in result["cohorts"]))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);self.write_campaign(root)
            result = aggregate(root)
            self.assertTrue(all(c["complete"] for c in result["cohorts"]))
            self.assertFalse(result["final_goal_verified"])
            self.assertFalse(result["large_scale_authorized"])
            self.assertFalse(any(c["first_skill_candidate"] for c in result["cohorts"]))

    def test_mixed_dependencies_sessions_and_paired_initial_traces_are_refused(self):
        for key in ("torch", "imitation_admission"):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder);self.write_campaign(root)
                path = root / "runs" / contract()["runs"][-1]["name"] / "manifest.json"
                record = json.loads(path.read_text())
                if key == "torch":record[key] = "different"
                else:record[key]["session"] = "imitation-other"
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "Mixed"):
                    aggregate(root)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);self.write_campaign(root)
            path = root / "runs" / contract()["runs"][1]["name"] / "evaluation.json"
            record = json.loads(path.read_text());record["untrained"][0]["trace"][0]["body_hit_frames"] = 1
            record["untrained"][0]["final"]["body_hit_frames"] = 1
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, "initial reference"):
                aggregate(root)

    def test_prepare_requires_complete_failed_timing_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch("research.imitation_campaign.timing_aggregate", return_value={
                "missing_runs": [1], "rows": [], "cohorts": []}):
                with self.assertRaisesRegex(ValueError, "complete timing"):
                    prepare(root / "new", root / "timing", root / "data")
            self.assertFalse((root / "new").exists())

    def test_dataset_declarations_use_canonical_json_warmup_descriptors(self):
        cases = contract()["study"]["data"]["cases"]
        record = {"episodes": [{
            "case": case, "controlled_ticks": 600, "reset_settling_ticks": 120,
            "final": {"milestone_contract": contract()["study"]["evaluation"]["benchmarks"]}}
            for case in cases], "data_sha256": "e" * 64, "expert_source_sha256": "f" * 64,
            "samples": 9}
        arrays = {"eligible": np.ones(9, dtype=np.bool_),
                  "observations": np.zeros((9, 217), dtype=np.float32)}
        with patch("research.imitation_campaign.load", return_value=(arrays, record)):
            result = dataset_contract(Path.cwd(), PROVENANCE)
        self.assertEqual(result["eligible_samples"], 9)
        self.assertTrue(result["normalization_contract"]["frozen"])


if __name__ == "__main__":
    unittest.main()
