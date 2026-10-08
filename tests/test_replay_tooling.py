import json, os, tempfile, unittest
from pathlib import Path
from unittest import mock

from explore import replay_route as rr
from research import cdp_browser


class TraceCompareTests(unittest.TestCase):
    def setUp(self):
        self.ref = {t: (float(t), 2.0 * t) for t in range(1, 101)}

    def test_identical_is_bit_exact(self):
        got = [(t, x, y) for t, (x, y) in self.ref.items()]
        rep = rr.compare_traces(self.ref, got, 1e-6)
        self.assertEqual(rep["verdict"], "BIT-EXACT")
        self.assertIsNone(rep["first_bit_difference"])

    def test_reports_first_tick_over_eps_and_first_bit_difference(self):
        got = []
        for t, (x, y) in self.ref.items():
            dx = 1e-12 if t >= 10 else 0.0       # below eps: bit difference only
            dy = 0.5 if t >= 60 else 0.0         # above eps
            got.append((t, x + dx, y + dy))
        rep = rr.compare_traces(self.ref, got, 1e-6)
        self.assertEqual(rep["first_bit_difference"]["tick"], 10)
        self.assertEqual(rep["first_divergence_over_eps"]["tick"], 60)
        self.assertEqual(rep["verdict"], "DIVERGED")
        self.assertEqual(rep["final_tick_compared"], 100)

    def test_tiny_drift_is_within_eps(self):
        got = [(t, x + 1e-9, y) for t, (x, y) in self.ref.items()]
        self.assertEqual(rr.compare_traces(self.ref, got, 1e-6)["verdict"], "WITHIN-EPS (not bit-exact)")

    def test_trace_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            ticks = [(1, 0.1 + 0.2, 21.0), (2, 1 / 3, 5e-324)]
            rr.write_trace(p, {"os": "x"}, 0, ticks)
            meta, rows = rr.load_trace(p)
            self.assertEqual(rows[1], (0.1 + 0.2, 21.0)); self.assertEqual(rows[2], (1 / 3, 5e-324))
            self.assertEqual(meta["os"], "x")


class ChromeDiscoveryTests(unittest.TestCase):
    def test_override_and_missing_override(self):
        with tempfile.NamedTemporaryFile() as f, mock.patch.dict(os.environ, {"RL_CHROME_BINARY": f.name}):
            self.assertEqual(cdp_browser.find_chrome(), f.name)
        with mock.patch.dict(os.environ, {"RL_CHROME_BINARY": "/nonexistent/chrome"}):
            with self.assertRaises(RuntimeError):
                cdp_browser.find_chrome()

    def test_windows_program_files_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "Google" / "Chrome" / "Application" / "chrome.exe"
            exe.parent.mkdir(parents=True); exe.write_text("")
            env = {"PROGRAMFILES": d}
            with mock.patch.dict(os.environ, env), mock.patch.object(cdp_browser.sys, "platform", "win32"):
                os.environ.pop("RL_CHROME_BINARY", None)
                self.assertEqual(cdp_browser.find_chrome(), str(exe))


class HudTextTests(unittest.TestCase):
    def test_success_line(self):
        text = rr.hud_text(0, 1.0, 13937, 13940, "ROUTE", 0, 0, 3589.23, 16000.81, 16000.81, None, None, True)
        self.assertIn("SUCCESS", text)
        self.assertIn("16000.81", text)

    def test_hold_outcome_line_without_success(self):
        text = rr.hud_text(0, 1.0, 9424, 9604, "HOLD", 180, 180, 4974.5, 9338.9, 9341.0,
                           (4973.3, 9341.0), {"held": True, "gain": 9317.9})
        self.assertIn("HOLD COMPLETE 180/180: HELD", text)
        self.assertNotIn("SUCCESS", text)


if __name__ == "__main__":
    unittest.main()
