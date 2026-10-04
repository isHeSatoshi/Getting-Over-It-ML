import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from research.provenance import fingerprint
from research.visible_replay import current_game_contract, main


class VisibleReplayTests(unittest.TestCase):
    def test_detached_game_contract_matches_normal_fingerprint_without_git(self):
        expected = fingerprint()
        with patch("subprocess.run", side_effect=AssertionError("Viewer must not need Git")):
            actual = current_game_contract()
        for key in ("project_sha256", "runtime_sha256", "asset_set_sha256"):
            self.assertEqual(actual[key], expected[key])
        for key, value in actual["source_sha256"].items():
            self.assertEqual(value, expected["source_sha256"][key])

    def test_viewer_budget_and_relative_inputs_fail_before_opening_chrome(self):
        for minutes in (0, 31):
            argv = ["viewer", "--trial", str(Path.cwd() / "absent"),
                    "--campaign", str(Path.cwd() / "absent.json"),
                    "--status", str(Path.cwd() / "status.json"), "--minutes", str(minutes)]
            with patch("sys.argv", argv), self.assertRaises(ValueError):
                main()
        with patch("sys.argv", ["viewer", "--trial", "relative", "--campaign", "relative",
                               "--status", "relative"]), self.assertRaises(ValueError):
            main()


if __name__ == "__main__":
    unittest.main()
