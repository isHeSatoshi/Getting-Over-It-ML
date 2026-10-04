import unittest

from research.settled_hold import SettledHoldMonitor, contract


def state(_tick, **changes):
    return dict({"tick": _tick, "physics_hz": 30, "player_world_x": 320.,
                 "player_world_y": 104., "player_vx": 0., "player_vy": 0.,
                 "body_collision": True, "dead": False, "success": False}, **changes)


class SettledHoldTests(unittest.TestCase):
    def test_contract_retains_original_metric_and_independent_bounded_clocks(self):
        record = contract()
        self.assertEqual((record["settling_cap_ticks"], record["hold_ticks"]), (30, 90))
        self.assertEqual(record["region_and_support"]["max_speed_per_tick"], 2)
        self.assertFalse(record["changes_original_milestone"])
        self.assertFalse(record["teacher_data_admission"])

    def test_settling_sample_is_excluded_and_full90_hold_required(self):
        monitor = SettledHoldMonitor()
        monitor.advance(state(100, player_vx=3))
        monitor.advance(state(101))
        self.assertEqual(monitor.summary()["hold_ticks"], 0)
        for tick in range(102, 191):
            monitor.advance(state(tick))
        self.assertEqual(monitor.hold_ticks, 89)
        self.assertFalse(monitor.summary()["passed"])
        result = monitor.advance(state(191))
        self.assertTrue(result["passed"])
        self.assertEqual(result["hold_start_physics_tick"], 102)

    def test_timeout_at30_is_final_no_rearming(self):
        monitor = SettledHoldMonitor()
        for tick in range(30):
            result = monitor.advance(state(tick, player_world_x=294))
        self.assertEqual(result["reason"], "settling_timeout")
        self.assertFalse(monitor.advance(state(30))["passed"])
        self.assertEqual(monitor.settle_ticks, 30)

    def test_last_allowed_settling_tick_can_start_hold(self):
        monitor = SettledHoldMonitor()
        for tick in range(29):
            monitor.advance(state(tick, body_collision=False))
        self.assertEqual(monitor.advance(state(29))["phase"], "holding")
        self.assertEqual(monitor.settle_ticks, 30)

    def test_region_speed_loss_fails_without_restart(self):
        monitor = SettledHoldMonitor()
        monitor.advance(state(0))
        self.assertEqual(monitor.advance(state(1, player_vx=2.01))["reason"], "hold_region_or_speed_lost")
        self.assertFalse(monitor.advance(state(2))["passed"])
        self.assertEqual(monitor.hold_ticks, 0)

    def test_body_contact_fraction_is_original_point8(self):
        for hits, passed in ((72, True), (71, False)):
            monitor = SettledHoldMonitor()
            monitor.advance(state(0))
            for tick in range(1, 91):
                result = monitor.advance(state(tick, body_collision=tick <= hits))
            self.assertEqual(result["passed"], passed)
            self.assertEqual(result["hold_body_hits"], hits)

    def test_invalid_physics_clock_nonfinite_and_skips_fail(self):
        monitor = SettledHoldMonitor()
        for changes in ({"player_vx": float("nan")}, {"physics_hz": 60}, {"tick": True}):
            with self.assertRaises(ValueError):
                monitor.advance(state(0, **changes))
        monitor.advance(state(5))
        for tick in (5, 7):
            with self.assertRaises(ValueError):
                monitor.advance(state(tick))

    def test_terminal_during_settling_or_holding_fails(self):
        for after_settle in (False, True):
            monitor = SettledHoldMonitor()
            if after_settle:
                monitor.advance(state(0))
            result = monitor.advance(state(1, dead=True))
            self.assertEqual(result["reason"], "terminal_state")
            self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
