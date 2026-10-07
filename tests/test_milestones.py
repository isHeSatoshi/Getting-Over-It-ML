import unittest
from research.milestones import FIRST_LEDGE, MilestoneTracker


def state(x=320, y=104, vx=0, vy=0, body=True, hammer=False):
    return {"player_world_x": x, "player_world_y": y, "player_vx": vx, "player_vy": vy,
            "body_collision": body, "hammer_collision": hammer, "dead": False, "success": False}


class MilestoneTests(unittest.TestCase):
    def test_requires_full_hold_and_body_support(self):
        tracker = MilestoneTracker()
        tracker.advance([state()] * 89)
        self.assertFalse(tracker.summary()["milestone_success"][FIRST_LEDGE.name])
        tracker.advance([state()])
        self.assertTrue(tracker.summary()["milestone_success"][FIRST_LEDGE.name])
        self.assertEqual(tracker.summary()["milestone_success_seconds"][FIRST_LEDGE.name], 3)

    def test_transient_jump_and_low_ground_do_not_succeed(self):
        for sequence in ([state()] * 30 + [state(y=50)] * 90,
                         [state(x=0, y=104)] * 100, [state(y=55)] * 100,
                         [state(vy=4)] * 100, [state(body=False, hammer=True)] * 100):
            tracker = MilestoneTracker()
            tracker.advance(sequence)
            self.assertFalse(tracker.summary()["milestone_success"][FIRST_LEDGE.name])

    def test_leaving_region_resets_hold_but_not_earned_success(self):
        tracker = MilestoneTracker()
        tracker.advance([state()] * 60 + [state(x=400)] + [state()] * 60)
        self.assertFalse(tracker.summary()["milestone_success"][FIRST_LEDGE.name])
        tracker.advance([state()] * 30)
        self.assertTrue(tracker.summary()["milestone_success"][FIRST_LEDGE.name])
        tracker.advance([state(x=400)])
        self.assertTrue(tracker.summary()["milestone_success"][FIRST_LEDGE.name])

    def test_reset_removes_previous_episode_success(self):
        tracker = MilestoneTracker()
        tracker.advance([state()] * 90)
        tracker.reset()
        self.assertFalse(tracker.summary()["milestone_success"][FIRST_LEDGE.name])


if __name__ == "__main__":
    unittest.main()
