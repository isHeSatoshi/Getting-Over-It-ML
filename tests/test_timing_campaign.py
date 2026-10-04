from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.evaluation_cases import STANDARD_CASES
from research.milestones import FIRST_LEDGE
from research.reward import RewardConfig
from research.study_metrics import benchmark_contract
from research.timing_campaign import aggregate, command, contract, prepare, summarize_evaluation, validate_run
from research.training_timing import training_settings


PROVENANCE = {"project_sha256": "a" * 64, "runtime_sha256": "b" * 64,
              "asset_set_sha256": "c" * 64, "source_sha256": {"synthetic-fixture": "d" * 64}}


def evaluation_fixture(repeat, decisions):
    """Terminal orchestration data only, not legal real-game policy evidence."""
    records = []
    for case in STANDARD_CASES:
        prediction = np.zeros((1, 2), dtype=np.float32)
        applied = PhysicalCaseClock(case).apply(prediction, 0)[0].tolist()
        final = {
            "action": prediction[0].tolist(), "applied_action": applied,
            "backend": "turbowarp-real-renderer", "physics_ticks": 1,
            "body_hit_frames": 0, "hammer_hit_frames": 0,
            "success": False, "dead": True, "player_world_y": -181, "retained_gain": -202,
            "milestone_contract": benchmark_contract(True),
            "milestone_success": {item["name"]: False for item in benchmark_contract(True)},
            "milestone_success_seconds": {item["name"]: None for item in benchmark_contract(True)},
        }
        records.append({
            "case": json.loads(json.dumps(case.describe())), "seed": case.reset_seed,
            "final": final, "trace": [final], "decisions": 1,
            "timing_contract": {"version": "physical-case-evaluation-v1", "frame_skip": repeat,
                                "physics_hz": 30.0, "perturbation_hold_ticks": 4,
                                "requested_physics_ticks": decisions * repeat},
            "controlled_physics_ticks": 1, "reset_settling_physics_ticks": 240,
        })
    return records


def run_fixture(run):
    repeat, steps = run["frame_skip"], run["steps"]
    timing = training_settings("ppo", False, frame_skip=repeat, timing_study=True)
    manifest = {
        **deepcopy(PROVENANCE), "purpose": "remote research run", "device": "cpu", "steps": steps,
        "python": "synthetic-3.11", "numpy": "synthetic-2", "torch": "synthetic-cpu",
        "stable_baselines3": "synthetic-sb3",
        "config": {"algorithm": "ppo", "action": "absolute", "seed": run["seed"], "frame_skip": repeat,
                   "steps": steps, "backend": "fast", "reward_profile": "settled", "discount_half_life": 120,
                   "evaluation_decisions": timing["evaluation_decisions"], "evaluation_suite": "standard",
                   "replay_buffer_size": 200000, "smoke": False, "remote_training": True,
                   "timing_study": True, "no_terrain": False},
        "control_timing_contract": timing, "reward_contract": RewardConfig().describe(repeat),
        "reward_normalization": {"enabled": False, "clipping": "disabled", "units": "raw_task_units"},
        "evaluation_contract": {"suite": "standard", "cases": json.loads(json.dumps(
            [case.describe() for case in STANDARD_CASES])), "decisions": timing["evaluation_decisions"],
            "benchmarks": benchmark_contract(True)},
        "optimizer_work_contract": {"version": "optimizer-step-calls-v1"},
    }
    resets = steps // timing["episode_decisions"] + 1
    work = {"version": "controlled-reset-ticks-v1",
            "scope": "Training environment only; excludes preflight, evaluation and runtime boot",
            "frame_skip": repeat, "decision_steps": steps,
            "nominal_controlled_physics_ticks": steps * repeat, "controlled_physics_ticks": steps * repeat,
            "resets": resets, "reset_settling_physics_ticks": resets * 120,
            "total_counted_physics_ticks": steps * repeat + resets * 120, "terminal_short_decisions": 0}
    training = {"control_timing_contract": timing, "complete": True, "actual_transitions": steps,
                "requested_transitions": steps, "learner_gamma": timing["gamma"],
                "learner_gae_lambda": timing["gae_lambda"], "torch_threads": 1,
                "learning_wall_seconds": 10.0, "physical_work": work,
                "optimizer_work": {"version": "optimizer-step-calls-v1", "algorithm": "ppo",
                                   "optimizer_step_calls": {"policy": 3840},
                                   "total_optimizer_step_calls": 3840, "sb3_internal_update_counter": 480}}
    evaluation = {"training_backend": "fast", "evaluation_backend": "reference",
                  "before": evaluation_fixture(repeat, timing["evaluation_decisions"]),
                  "after": evaluation_fixture(repeat, timing["evaluation_decisions"])}
    return manifest, training, evaluation


class TimingCampaignTests(unittest.TestCase):
    def test_contract_pairs_six_declared_runs_and_preserves_nonexecution(self):
        declared = contract()
        self.assertEqual(len(declared["runs"]), 6)
        self.assertEqual([(run["seed"], run["frame_skip"]) for run in declared["runs"]],
                         [(3, 1), (3, 4), (4, 1), (4, 4), (5, 1), (5, 4)])
        self.assertEqual(declared["study"]["state"], "prepared_only_not_executable")
        self.assertIn("No runner", declared["admission"])

    def test_commands_validate_run_and_paths_without_launching(self):
        run = contract()["runs"][0]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new"
            args = command(run, output)
            self.assertIn("--remote-training", args)
            self.assertIn("--timing-study", args)
            self.assertIn(str(run["steps"]), args)
            smoke = command(run, output, smoke=True)
            self.assertIn("--smoke", smoke)
            self.assertIn("256", smoke)
            self.assertFalse(output.exists())
            output.mkdir()
            with self.assertRaises(ValueError):
                command(run, output)
        with self.assertRaises(ValueError):
            command({**run, "seed": 0}, Path("relative"))

    def test_prepare_requires_complete_ineligible_pilot_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "study"
            with patch("research.timing_campaign.pilot_aggregate", return_value={
                "missing_runs": ["missing"], "rows": [], "followup_eligible_variants": [],
                "scale_eligible_variants": []}):
                with self.assertRaisesRegex(ValueError, "complete pilot"):
                    prepare(target, root / "pilot")
            self.assertFalse(target.exists())

    def test_validated_synthetic_run_reports_actual_work_and_two_metrics(self):
        for run in contract()["runs"]:
            row = validate_run(*run_fixture(run), run, PROVENANCE)
            self.assertEqual(row["after"]["deaths"], 9)
            self.assertEqual(row["after"]["controlled_physics_ticks"], 9)
            self.assertEqual(row["after"]["holds"][FIRST_LEDGE.name], 0)
            self.assertEqual(row["training_physical_work"]["controlled_physics_ticks"], 393216)

    def test_smoke_legacy_reward_clock_and_source_drift_are_refused(self):
        run = contract()["runs"][0]
        for mutate in (
            lambda m, t, e: m["config"].update(smoke=True),
            lambda m, t, e: m["config"].update(timing_study=False),
            lambda m, t, e: m["config"].update(seed=0),
            lambda m, t, e: m["reward_contract"].update(gamma=0.5),
            lambda m, t, e: m["reward_normalization"].update(enabled=True),
            lambda m, t, e: m.update(project_sha256="wrong"),
            lambda m, t, e: t.update(learner_gae_lambda=0.95),
            lambda m, t, e: t["optimizer_work"].update(total_optimizer_step_calls=480),
            lambda m, t, e: t["physical_work"].update(controlled_physics_ticks=1),
            lambda m, t, e: t["physical_work"].update(resets=1),
            lambda m, t, e: t["physical_work"].update(scope="includes evaluator resets"),
            lambda m, t, e: e.update(evaluation_backend="fast"),
        ):
            artifacts = run_fixture(run)
            mutate(*artifacts)
            with self.assertRaises(ValueError):
                validate_run(*artifacts, run, PROVENANCE)

    def test_realized_short_steps_are_allowed_but_counted_separately(self):
        run = contract()["runs"][1]
        manifest, training, evaluation = run_fixture(run)
        work = training["physical_work"]
        work.update(controlled_physics_ticks=393213, terminal_short_decisions=1,
                    total_counted_physics_ticks=393213 + work["reset_settling_physics_ticks"])
        result = validate_run(manifest, training, evaluation, run, PROVENANCE)
        self.assertEqual(result["training_physical_work"]["controlled_physics_ticks"], 393213)
        work["terminal_short_decisions"] = 0
        with self.assertRaisesRegex(ValueError, "short-step"):
            validate_run(manifest, training, evaluation, run, PROVENANCE)

    def test_changed_perturbations_contacts_metrics_and_finals_are_refused(self):
        for mutate in (
            lambda r: r[0]["case"].update(reset_seed=1),
            lambda r: r[0]["timing_contract"].update(perturbation_hold_ticks=1),
            lambda r: r[0].update(controlled_physics_ticks=4),
            lambda r: r[0]["trace"][0].update(body_hit_frames=5),
            lambda r: r[0]["trace"][0].update(applied_action=[0.5, 0.5]),
            lambda r: r[0]["trace"][0].update(success=True),
            lambda r: r[0]["trace"][0].update(milestone_contract=[FIRST_LEDGE.__dict__]),
            lambda r: r[0].update(final={}),
        ):
            records = evaluation_fixture(4, 450)
            mutate(records)
            with self.assertRaises(ValueError):
                summarize_evaluation(records, 4, 450)

    def write_campaign(self, root, all_runs=False):
        (root / "timing_campaign.json").write_text(json.dumps({
            "contract": contract(), "provenance": PROVENANCE}), encoding="utf-8")
        runs = contract()["runs"] if all_runs else contract()["runs"][:1]
        for run in runs:
            path = root / "runs" / run["name"]
            path.mkdir(parents=True)
            for filename, value in zip(("manifest.json", "training_summary.json", "evaluation.json"),
                                       run_fixture(run)):
                (path / filename).write_text(json.dumps(value), encoding="utf-8")

    def test_missing_companions_cannot_complete_a_cohort_or_compare_arms(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_campaign(root)
            result = aggregate(root)
            self.assertEqual(len(result["missing_runs"]), 5)
            self.assertFalse(any(cohort["complete"] for cohort in result["cohorts"]))
            self.assertEqual(result["repeat_1_minus_repeat_4_worst_seed_hold_rate"], {})
            path = root / "runs" / contract()["runs"][0]["name"] / "training_summary.json"
            path.unlink()  # Owned synthetic fixture only.
            self.assertEqual(len(aggregate(root)["missing_runs"]), 6)

    def test_complete_synthetic_matrix_never_authorizes_scale_or_final_goal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_campaign(root, all_runs=True)
            result = aggregate(root)
            self.assertEqual(result["missing_runs"], [])
            self.assertTrue(all(cohort["complete"] for cohort in result["cohorts"]))
            self.assertFalse(result["final_goal_verified"])
            self.assertFalse(result["large_scale_authorized"])
            path = root / "runs" / contract()["runs"][-1]["name"] / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["torch"] = "different-synthetic-version"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dependency"):
                aggregate(root)


if __name__ == "__main__":
    unittest.main()
