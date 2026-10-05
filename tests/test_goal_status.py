import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tools.hf_research_status import main


class GoalStatusTests(unittest.TestCase):
    def test_goal_monitor_reads_bounded_pinned_json_and_reports_physical_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            status, result = root/"status.json", root/"result.json"
            status.write_text(json.dumps({"phase": "goal_complete", "deadline_epoch": 3700}))
            result.write_text(json.dumps({"first_ledge_successes": 8, "nominal_height180_hold90": True,
                "pilot_gate_passed": True, "summits": 0, "deaths": 0, "physics": {"total": 10000},
                "records": [{"retained_gain": 181}]*10}))
            session = "goal-fixture-1"
            prefix = f"{session}/goal_campaign/seed21/result.json"
            api = Mock()
            api.get_space_variables.return_value = {"RL_SESSION_ID": SimpleNamespace(value=session)}
            api.repo_info.side_effect = [SimpleNamespace(sha="a"*40),
                SimpleNamespace(private=True, siblings=[SimpleNamespace(rfilename=prefix, size=result.stat().st_size)])]
            api.list_repo_files.return_value = [f"{session}/control/status.json", prefix]
            output = io.StringIO()
            with patch("tools.hf_research_status.HfApi", return_value=api), \
                    patch("tools.hf_research_status.hf_hub_download",
                          side_effect=[str(status), str(result)]) as download, \
                    patch("tools.hf_research_status.subprocess.run",
                          return_value=SimpleNamespace(stdout='{"runtime":{"stage":"PAUSED"}}')), \
                    patch("sys.argv", ["status"]), contextlib.redirect_stdout(output):
                main()
            report = json.loads(output.getvalue())
            self.assertEqual(report["session"], session)
            self.assertEqual(report["completed_runs"][0]["first_ledge_successes"], 8)
            self.assertFalse(report["completed_runs"][0]["final_goal_verified"])
            self.assertTrue(all(call.kwargs["revision"] == "a"*40 for call in download.call_args_list))


if __name__ == "__main__":
    unittest.main()
