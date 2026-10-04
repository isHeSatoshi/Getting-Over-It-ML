from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.hf_research_status import campaign_prefix, selected_session, SESSION


class StatusSessionTests(unittest.TestCase):
    def test_configured_replacement_is_used_without_reading_other_variables(self):
        api = Mock()
        api.get_space_variables.return_value = {
            "RL_SESSION_ID": SimpleNamespace(value="poc-20261004-v2"),
            "unrelated": SimpleNamespace(value="do-not-display"),
        }
        self.assertEqual(selected_session(api), "poc-20261004-v2")

    def test_explicit_historical_session_avoids_variable_lookup(self):
        api = Mock()
        self.assertEqual(selected_session(api, "poc-20261004-v1"), "poc-20261004-v1")
        api.get_space_variables.assert_not_called()

    def test_missing_variable_uses_original_session(self):
        api = Mock()
        api.get_space_variables.return_value = {}
        self.assertEqual(selected_session(api), SESSION)

    def test_invalid_session_cannot_escape_artifact_prefix(self):
        for session in ("", "../other", "session/other"):
            with self.subTest(session=session):
                with self.assertRaises(ValueError):
                    selected_session(Mock(), session)

    def test_timing_monitor_uses_only_its_own_runs_not_imported_pilot(self):
        prefix = campaign_prefix("timing-synthetic-1")
        self.assertEqual(prefix, "timing-synthetic-1/timing_campaign/runs/")
        self.assertFalse("timing-synthetic-1/prior_pilot/runs/model/evaluation.json".startswith(prefix))
        self.assertEqual(campaign_prefix("poc-20261004-v2"),
                         "poc-20261004-v2/pilot_campaign/runs/")

    def test_imitation_monitor_excludes_imported_timing_results(self):
        prefix = campaign_prefix("imitation-synthetic-1")
        self.assertEqual(prefix, "imitation-synthetic-1/imitation_campaign/runs/")
        self.assertFalse("imitation-synthetic-1/prior_timing/runs/model/evaluation.json".startswith(prefix))


if __name__ == "__main__":
    unittest.main()
