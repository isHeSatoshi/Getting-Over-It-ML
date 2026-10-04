from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.linux_noise_probe import PLAN_SHA, contract, execute, validate_report


def result():
    conditions = contract()["conditions"]
    return {"version": "causal-noise-prefix-suffix-probe-v1", "plan_sha256": PLAN_SHA,
            "training_updates": 0, "case_rollouts": 8, "controlled_ticks": 14400, "reset_ticks": 1920,
            "status": "completed_exploratory_diagnostic",
            "rollouts": {key: {backend: {"control_ticks": 1800, "reset_ticks": 240}
                              for backend in ("reference", "fast")} for key in conditions},
            "backend_differences": {key: None for key in conditions},
            "remote_differences": {"nominal": None, "full_noise_8105": None}}


class LinuxProbeTests(unittest.TestCase):
    def test_complete_fixed_protocol_is_exploratory_not_goal(self):
        self.assertEqual(validate_report(result()), "completed_exploratory_diagnostic")
        self.assertFalse(contract()["goal_promotion"])
        self.assertEqual(contract()["training_updates"], 0)

    def test_failed_baseline_can_stop_but_never_execute_interventions(self):
        data = result()
        data["status"] = "baseline_fidelity_or_portability_failed"
        data["rollouts"] = {key: data["rollouts"][key] for key in ("nominal", "full_noise_8105")}
        data["case_rollouts"] = 4;data["controlled_ticks"] = 7200;data["reset_ticks"] = 960
        data["remote_differences"]["nominal"] = {"tick": 1}
        self.assertEqual(validate_report(data), data["status"])
        data["rollouts"]["early_noise_8105"] = {}
        with self.assertRaisesRegex(ValueError, "bypassed"):
            validate_report(data)

    def test_missing_comparisons_and_expanded_work_are_refused(self):
        for key, value in (("controlled_ticks", 14401), ("reset_ticks", 1921),
                           ("case_rollouts", 9), ("training_updates", 1)):
            data = result();data[key] = value
            with self.assertRaises(ValueError):
                validate_report(data)
        for key in ("remote_differences", "backend_differences"):
            data = result();data[key] = {}
            with self.assertRaises(ValueError):
                validate_report(data)

    def test_desktop_transport_fails_before_original_worker_or_browsers(self):
        with tempfile.TemporaryDirectory() as directory:
            grant = Path(directory) / "grant.json";grant.write_text("{}")
            with patch("tools.linux_noise_probe.sys.platform", "win32"), \
                    patch("tools.linux_noise_probe.worker") as original:
                with self.assertRaisesRegex(ValueError, "isolated Linux"):
                    execute(grant)
                original.assert_not_called()

    def test_monitor_marks_hold_as_event_not_robust_success(self):
        from tools.hf_research_status import noise_probe_summary
        payload = {"training_updates": 0, "controlled_ticks": 1800,
                   "reset_ticks": 240, "case_rollouts": 1, "status": "baseline_running",
                   "rollouts": {"nominal": {"reference": {"final": {
                       "retained_gain": 83, "success": False, "dead": False,
                       "milestone_success": {"first_ledge_v1": True,
                                             "first_platform_support_diagnostic_v2": True}}}}}}
        summary = noise_probe_summary(payload)
        self.assertTrue(summary["reference_outcomes"]["nominal"]["central_held_event"])
        self.assertNotIn("success_rate", summary)
        payload["training_updates"] = 1
        with self.assertRaises(ValueError):
            noise_probe_summary(payload)


if __name__ == "__main__":
    unittest.main()
