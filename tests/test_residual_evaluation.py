from copy import deepcopy
import json
import unittest

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.fast_fidelity import NUMERIC, DISCRETE
from research.milestones import MilestoneTracker, FIRST_LEDGE
from research.residual_controller import ResidualController
from research.residual_evaluation import summarize
from research.residual_study import CASES
from research.study_metrics import benchmark_contract
from research.timing_probe import PLATFORM_SUPPORT
from tests.test_residual_env import fixture


def synthetic_death_records():
    """Contract-test fixtures only, never game/evaluation evidence."""
    prior, actions = fixture()
    records = []
    for case in CASES:
        controller = ResidualController(prior, actions)
        pre = prior[0].copy()
        controller.reset(pre)
        actor = controller.prepare(pre)
        issued = controller.action(np.zeros(2, np.float32))
        applied = PhysicalCaseClock(case).apply(issued[None, :], 0)[0]
        post = pre.copy()
        post[1] = -200/16000
        state = {key: 0 for key in NUMERIC+DISCRETE}
        state.update(tick=121, frame_id=121, physics_hz=30, command_id_applied=1,
                     game_time=121/30, player_world_y=-200, player_vy=-221,
                     hammer_world_y=-200, hammer_vy=-221,
                     success=False, dead=True, body_collision=False, hammer_collision=False,
                     backend="turbowarp-real-renderer", schema_version=2)
        tracker = MilestoneTracker((FIRST_LEDGE, PLATFORM_SUPPORT), physics_hz=30)
        tracker.reset()
        tracker.advance([state])
        observed = controller.observe(post, applied, terminated=True, truncated=False)
        next_actor = post.tolist()+[float(np.float32(1/599)), *actions[1].tolist(), *issued.tolist()]
        row = {"physics_ticks": 1, "body_hit_frames": 0, "hammer_hit_frames": 0,
               "backend": state["backend"], "success": False, "dead": True,
               "player_world_x": 0, "player_world_y": -200, "retained_gain": -221,
               "milestone_contract": benchmark_contract(True), **tracker.summary(),
               "action": issued.tolist(), "applied_action": applied.tolist(), "residual": [0., 0.],
               "actor_input": actor.tolist(), "next_actor_input": next_actor,
               "transition": observed, "reward": -5., "terminated": True, "truncated": False,
               "state": state}
        records.append({"case": json.loads(json.dumps(case.describe())), "seed": case.reset_seed,
                        "trace": [row], "final": row, "decisions": 1,
                        "controlled_physics_ticks": 1, "reset_settling_physics_ticks": 120})
    return records


class ResidualEvaluationTests(unittest.TestCase):
    def test_short_terminal_fixture_counted_as_death_not_climb_or_hold(self):
        summary = summarize(synthetic_death_records(), zero_actor=True)
        self.assertEqual(summary["deaths"], 9)
        self.assertEqual(summary["full_completions"], 0)
        self.assertEqual(summary["holds"]["first_ledge_v1"], 0)
        self.assertEqual(summary["controlled_physics_ticks"], 9)
        self.assertEqual(summary["reset_settling_physics_ticks"], 1080)

    def test_changed_case_clock_or_actual_application_rejected(self):
        records = synthetic_death_records()
        records[0]["case"]["reset_seed"] = 15002
        with self.assertRaises(ValueError):
            summarize(records)
        records = synthetic_death_records()
        records[1]["trace"][0]["applied_action"] = [0., 0.]
        with self.assertRaisesRegex(ValueError, "clock"):
            summarize(records)

    def test_context_history_mismatch_old217_or_false_zeroactor_rejected(self):
        for mutate in (
            lambda row: row["actor_input"].__setitem__(220, .5),
            lambda row: row.update(next_actor_input=row["next_actor_input"][:217]),
            lambda row: row.update(residual=[.1, 0.]),
        ):
            records = synthetic_death_records()
            mutate(records[0]["trace"][0])
            with self.assertRaises(ValueError):
                summarize(records, zero_actor=True)

    def test_fabricated_hold_flag_or_summit_inconsistent_with_physics_rejected(self):
        records = synthetic_death_records()
        records[0]["trace"][0]["milestone_success"]["first_ledge_v1"] = True
        with self.assertRaisesRegex(ValueError, "holds"):
            summarize(records)
        records = synthetic_death_records()
        records[0]["trace"][0]["success"] = True
        with self.assertRaisesRegex(ValueError, "height"):
            summarize(records)

    def test_duplicate_case_bad_reset_count_and_false_tick_rejected(self):
        for mutate in (
            lambda records: records.__setitem__(1, deepcopy(records[0])),
            lambda records: records[0].update(reset_settling_physics_ticks=240),
            lambda records: records[0]["trace"][0]["state"].update(tick=122),
        ):
            records = synthetic_death_records()
            mutate(records)
            with self.assertRaises(ValueError):
                summarize(records)


if __name__ == "__main__":
    unittest.main()
