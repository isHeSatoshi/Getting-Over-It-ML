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

    def test_extra_local_ticks_stay_bit_exact(self):
        got = [(t, x, y) for t, (x, y) in self.ref.items()] + [(101, 0.0, 0.0), (102, 0.0, 0.0)]
        rep = rr.compare_traces(self.ref, got, 1e-6)
        self.assertEqual(rep["verdict"], "BIT-EXACT")
        self.assertEqual(rep["extra_local_ticks"], 2)
        self.assertTrue(rep["reference_complete"])

    def test_missing_local_ticks_are_not_bit_exact(self):
        got = [(t, x, y) for t, (x, y) in self.ref.items() if t <= 90]
        rep = rr.compare_traces(self.ref, got, 1e-6)
        self.assertEqual(rep["verdict"], "WITHIN-EPS (not bit-exact)")
        self.assertFalse(rep["reference_complete"])

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


class EndingPlaybackTests(unittest.TestCase):
    """The after-success phase keeps stepping so the project's own ending scripts can run."""

    class FakeBridge:
        def __init__(self, win_tick=3):
            self.tick = 0; self.win_tick = win_tick; self.after_flags = []; self.evaluated = []

        def reset(self, seed=0):
            self.tick = 0
            return {"tick": 0}

        def evaluate(self, expression):
            self.evaluated.append(expression)
            return None

        def step_commands(self, commands, after=False):
            self.after_flags.append(after)
            out = []
            for _ in commands:
                self.tick += 1
                out.append({"tick": self.tick, "player_world_x": float(self.tick), "player_world_y": 16001.0 if self.tick >= self.win_tick else 21.0,
                            "dead": False, "success": self.tick >= self.win_tick, "camera_x": 0.0, "camera_y": 0.0, "frame_id": self.tick})
                if self.tick >= self.win_tick and not after: break
            return out

    def replay(self, after_success=0, fastest_frames=None, actions=6):
        b = self.FakeBridge()
        out, ticks = rr.run(b, [[1.0, 1.0]] * actions, 1, 0, 0.0, None, 0, False, 1.0, None, 1,
                               after_success, 1.0, fastest_frames)
        return b, out, ticks

    def test_no_after_success_stops_at_the_win_flag(self):
        b, out, ticks = self.replay()
        self.assertTrue(out["success"])
        self.assertNotIn("ending_ticks", out)
        self.assertNotIn(True, b.after_flags)

    def test_after_success_keeps_stepping_and_reports_ending_state(self):
        b, out, ticks = self.replay(after_success=5)
        self.assertIn(True, b.after_flags)
        self.assertEqual(out["ending_ticks"], 5)
        self.assertEqual(out["ending_y"], 16001.0)
        self.assertFalse(out["ending_dead"])
        self.assertEqual(out["ticks"], 3)                       # route summary still ends at the win tick
        self.assertEqual(len(ticks), 3 + 5)                     # trace keeps the ending ticks

    def test_fastest_frames_is_applied_before_the_route(self):
        b, _, _ = self.replay(fastest_frames=3000)
        self.assertEqual(len(b.evaluated), 1)
        self.assertIn("3000", b.evaluated[0])
        self.assertIn("FASTEST", rr.SET_FASTEST_JS)


if __name__ == "__main__":
    unittest.main()
