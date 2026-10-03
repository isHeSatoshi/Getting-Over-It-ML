import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.milestones import FIRST_LEDGE
from research.timing_probe import (
    hold_targets, load_trajectory, replay_targets, support_metrics, PLATFORM_SUPPORT)
from research.milestones import MilestoneTracker


class TimingProbeTests(unittest.TestCase):
    def commands(self):
        return [{"x": index, "y": -index, "id": index + 1} for index in range(12)]

    def test_one_tick_keeps_targets_and_ids(self):
        commands = self.commands()
        self.assertEqual(hold_targets(commands, 1), commands)

    def test_four_tick_zero_phase_matches_original_hold(self):
        result = hold_targets(self.commands(), 4)
        self.assertEqual([row["x"] for row in result], [0] * 4 + [4] * 4 + [8] * 4)
        self.assertEqual([row["id"] for row in result], list(range(1, 13)))

    def test_phase_offsets_keep_initial_target_and_tick_budget(self):
        source = self.commands()
        saved = copy.deepcopy(source)
        result = hold_targets(source, 4, 2)
        self.assertEqual([row["x"] for row in result], [0, 0, 2, 2, 2, 2, 6, 6, 6, 6, 10, 10])
        self.assertEqual(len(result), len(source))
        self.assertEqual(source, saved)

    def test_invalid_timing_is_rejected(self):
        for repeat, phase in ((0, 0), (17, 0), (True, 0), (4, -1), (4, 4), (1.5, 0)):
            with self.subTest(repeat=repeat, phase=phase):
                with self.assertRaises(ValueError):
                    hold_targets(self.commands(), repeat, phase)
        with self.assertRaises(ValueError):
            hold_targets([], 4)

    def test_hold_uses_the_last_applied_coarse_target(self):
        commands = self.commands() + [{"x": 11, "y": -11, "id": index + 1}
                                      for index in range(12, 20)]
        result = replay_targets(commands, 4, motion_ticks=12)
        self.assertEqual([row["x"] for row in result[12:]], [8] * 8)
        self.assertEqual([row["id"] for row in result], list(range(1, 21)))

    def test_source_protocol_and_game_identity_are_checked(self):
        provenance = {"project_sha256": "project", "runtime_sha256": "runtime",
                      "asset_set_sha256": "assets",
                      "source_sha256": {"research/runtime.js": "physics",
                                        "research/collision_memo.js": "cache"}}
        report = {
            "provenance": provenance, "benchmark": FIRST_LEDGE.__dict__,
            "bounded_search": {"ticks_per_candidate_max": 600,
                               "best_knots": [[0, 0]] * 25},
            "search_reference_replay": {"milestone_success": {FIRST_LEDGE.name: True}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            commands, digest = load_trajectory(path, provenance)
            self.assertEqual(len(commands), 600)
            self.assertEqual(len(digest), 64)
            changed = copy.deepcopy(provenance)
            changed["asset_set_sha256"] = "different"
            with self.assertRaisesRegex(ValueError, "assets"):
                load_trajectory(path, changed)
            report["bounded_search"]["frame_skip"] = 4
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "per-tick"):
                load_trajectory(path, provenance)

    def test_secondary_edge_support_does_not_change_pilot_benchmark(self):
        trace = [{"player_world_x": 289.5, "player_world_y": 104,
                  "player_vx": 0, "player_vy": 0, "body_collision": True,
                  "dead": False, "success": False} for _ in range(90)]
        self.assertTrue(support_metrics(trace)["milestone_success"][PLATFORM_SUPPORT.name])
        original = MilestoneTracker()
        original.advance(trace)
        self.assertFalse(original.summary()["milestone_success"][FIRST_LEDGE.name])
        self.assertEqual(FIRST_LEDGE.x_min, 305)


if __name__ == "__main__":
    unittest.main()
