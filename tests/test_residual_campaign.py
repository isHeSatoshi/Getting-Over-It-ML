from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.residual_campaign import aggregate, validate_directory, write_evaluation, load_evaluation
from research.residual_study import SEEDS, TRANSITIONS, plan
from research.phase_controller import SOURCE_DATA_SHA
from tests.test_residual_evaluation import synthetic_death_records
from tests.test_timing_execution import CURRENT

CURRENT = deepcopy(CURRENT)
CURRENT["source_sha256"].update({"research/"+name: "d"*64 for name in
    ("residual_controller.py", "residual_env.py", "residual_policy.py", "stroke_controller.py")})


def write(path, value):
    path.write_text(json.dumps(value))


def prepared_fixture(root):
    """Synthetic validation files, not real training/model/physics evidence."""
    write(root/"residual_campaign.json", {"plan": plan(), "provenance": CURRENT})
    outputs = []
    for seed in SEEDS:
        output = root/"runs"/f"seed{seed}"
        output.mkdir(parents=True)
        admission = {"version": "residual-execution-admission-v1", "session": "residual-synthetic",
                     "seed": seed, "deadline_epoch": 3700, "source_space_revision": "a"*40,
                     "prior_data_sha256": SOURCE_DATA_SHA}
        scaffold = plan()["policy"]["adapter"]["scaffold"]
        checkpoint = {"schema": plan()["policy"], "source_sha256": {
            name: CURRENT["source_sha256"]["research/"+name] for name in
            ("residual_controller.py", "residual_env.py", "residual_policy.py", "stroke_controller.py")},
            "prior": {
            "observations": scaffold["base"]["nominal_pre_observations_sha256"],
            "actions": scaffold["base"]["nominal_applied_actions_sha256"]}}
        write(output/"manifest.json", {"version": "residual-trainer-v1",
            "purpose": "admitted remote residual PPO", "seed": seed, "plan": plan(),
            "provenance": CURRENT, "admission": admission, "checkpoint_contract": checkpoint,
            "python": "fixture", "numpy": "fixture", "torch": "fixture", "stable_baselines3": "fixture"})
        write(output/"training_summary.json", {"complete": True, "mock_smoke": False,
            "seed": seed, "plan": plan(), "ppo": plan()["ppo"], "transitions": TRANSITIONS,
            "physical": {"decision_steps": TRANSITIONS, "controlled_physics_ticks": TRANSITIONS,
                "frame_skip": 1, "resets": 73, "reset_settling_physics_ticks": 73*120,
                "total_counted_physics_ticks": TRANSITIONS+73*120},
            "optimizer": {"total_optimizer_step_calls": 128, "optimizer_step_calls": {"policy": 128}},
            "checkpoints": [65536, TRANSITIONS], "bootstrap_ticks": 240, "saved_reload_exact": True})
        for step in (65536, TRANSITIONS):
            model, rms = output/f"model_{step}.zip", output/f"normalizer_{step}.pkl"
            model.write_bytes(b"bounded mock bytes, never deserialized as a model")
            rms.write_bytes(b"bounded mock bytes, never deserialized as RMS")
            write(output/f"checkpoint_{step}.json", {"transitions": step, "contract": checkpoint,
                "admission": admission, "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
                "normalizer_sha256": hashlib.sha256(rms.read_bytes()).hexdigest()})
        for phase in ("baseline", "final"):
            write_evaluation(output, phase, synthetic_death_records())
        outputs.append(output)
    return outputs


class ResidualCampaignTests(unittest.TestCase):
    def test_synthetic_failed_cohort_never_claims_learned_benefit_or_goal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            prepared_fixture(root)
            result = aggregate(root)
            self.assertFalse(result["replicated_first_ledge_benefit"])
            self.assertEqual(result["goal_metrics"]["worst_seed_reference_completion_rate"], 0)
            self.assertFalse(result["goal_metrics"]["candidate_goal_passed"])
            self.assertFalse(result["final_goal_verified"])

    def test_mock_purpose_or_incomplete_work_cannot_count_as_training(self):
        with tempfile.TemporaryDirectory() as folder:
            output = prepared_fixture(Path(folder))[0]
            original = json.loads((output/"training_summary.json").read_text())
            for key, value in (("mock_smoke", True), ("complete", False), ("transitions", TRANSITIONS-1)):
                changed = deepcopy(original)
                changed[key] = value
                write(output/"training_summary.json", changed)
                with self.assertRaises(ValueError):
                    validate_directory(output, 12, CURRENT)

    def test_changed_policy_or_checkpoint_companion_hash_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = prepared_fixture(Path(folder))[0]
            (output/f"model_{TRANSITIONS}.zip").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "hashes"):
                validate_directory(output, 12, CURRENT)

    def test_mixed_sessions_deadlines_or_dependencies_cannot_form_three_seed_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            outputs = prepared_fixture(root)
            original = json.loads((outputs[1]/"manifest.json").read_text())
            original["torch"] = "other-fixture"
            write(outputs[1]/"manifest.json", original)
            with self.assertRaisesRegex(ValueError, "dependencies"):
                aggregate(root)

    def test_missing_run_or_inconsistent_actual_reset_count_is_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            output = prepared_fixture(Path(folder))[0]
            training = json.loads((output/"training_summary.json").read_text())
            training["physical"]["reset_settling_physics_ticks"] += 120
            write(output/"training_summary.json", training)
            with self.assertRaisesRegex(ValueError, "work"):
                validate_directory(output, 12, CURRENT)

    def test_case_index_hash_or_path_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = prepared_fixture(Path(folder))[0]
            index = json.loads((output/"evaluation_final.json").read_text())
            index["case_files"][0]["file"] = "../outside.json"
            write(output/"evaluation_final.json", index)
            with self.assertRaisesRegex(ValueError, "path"):
                load_evaluation(output, "final")
        with tempfile.TemporaryDirectory() as folder:
            output = prepared_fixture(Path(folder))[0]
            (output/"evaluation_final"/"nominal.json").write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, "hash"):
                load_evaluation(output, "final")


if __name__ == "__main__":
    unittest.main()
