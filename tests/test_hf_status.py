from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from tools.hf_research_status import selected_session, SESSION


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


if __name__ == "__main__":
    unittest.main()
