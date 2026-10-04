import unittest

import numpy as np

from research.env import BASE_FEATURES
from research.terminal_controller import TerminalController, contract


def fixture(x=320., y=104., hit=True, vx=0.):
    obs = np.zeros((600, 217), np.float32)
    obs[:, 0], obs[:, 1] = x/5500, y/16000
    obs[:, BASE_FEATURES.index("body_collision")] = hit
    obs[:, 2] = vx/64
    actions = np.zeros((600, 2), np.float32)
    return obs, actions


def prefix(controller, observation):
    for _ in range(600):
        controller.action(observation)
        controller.observe(observation)


class TerminalControllerTests(unittest.TestCase):
    def test_contract_has_no_case_seed_oracle_and_fixed_one_attempt(self):
        c = contract()
        self.assertFalse(c["case_seed_trace_index_input"])
        self.assertTrue(c["no_rearm"])
        self.assertEqual(c["arming_decision"], 600)
        self.assertEqual(c["maximum_decisions"], 751)

    def test_already_central_bypasses_and_never_rearms(self):
        obs, actions = fixture()
        controller = TerminalController(obs, actions)
        prefix(controller, obs[0])
        np.testing.assert_array_equal(controller.action(obs[0]), actions[599])
        edge = obs[0].copy()
        edge[0] = 294/5500
        controller.observe(edge)
        controller.action(edge)
        self.assertEqual(controller.phase, "bypass")
        self.assertFalse(controller.attempted)

    def test_unsupported_fast_or_outside_edge_does_not_trigger(self):
        for args in ((294, 104, False, 0), (294, 104, True, 3), (280, 104, True, 0),
                     (305, 104, True, 0), (306, 104, True, 0), (294, 90, True, 0)):
            obs, actions = fixture(*args)
            c = TerminalController(obs, actions)
            prefix(c, obs[0])
            c.action(obs[0])
            self.assertFalse(c.attempted)

    def test_plant_push_and_post_release_monitor_alignment(self):
        obs, actions = fixture(294)
        c = TerminalController(obs, actions)
        prefix(c, obs[0])
        for _ in range(30):
            np.testing.assert_array_equal(c.action(obs[0]), [26/128, -56/128])
            c.observe(obs[0])
        np.testing.assert_array_equal(c.action(obs[0]), [0., -56/128])
        central = fixture()[0][0]
        c.observe(central)
        self.assertEqual(c.monitor.settle_ticks, 0)
        c.action(central)
        c.observe(central)
        self.assertEqual(c.monitor.settle_ticks, 1)
        self.assertEqual(c.monitor.hold_ticks, 0)
        for _ in range(90):
            c.action(central)
            c.observe(central)
        self.assertEqual(c.phase, "succeeded")
        self.assertEqual(c.monitor.body_hits, 90)
        with self.assertRaises(ValueError):
            c.action(central)

    def test_exact_action_observe_pair_and_prepost_link_required(self):
        obs, actions = fixture()
        c = TerminalController(obs, actions)
        with self.assertRaises(ValueError):
            c.observe(obs[0])
        c.action(obs[0])
        with self.assertRaises(ValueError):
            c.action(obs[0])
        c.observe(obs[0])
        changed = obs[0].copy()
        changed[0] += .01
        with self.assertRaises(ValueError):
            c.action(changed)

    def test_budget_raw_input_and_reset_guards(self):
        obs, actions = fixture()
        c = TerminalController(obs, actions)
        with self.assertRaises(ValueError):
            c.action(obs[0].astype(np.float64))
        c.executed = 751
        with self.assertRaisesRegex(ValueError, "budget"):
            c.action(obs[0])
        c.reset()
        self.assertEqual(c.executed, 0)
        self.assertIsNone(c.monitor)
        self.assertFalse(c.attempted)

    def test_settling_failure_never_rearms(self):
        obs, actions = fixture(294)
        c = TerminalController(obs, actions)
        prefix(c, obs[0])
        for _ in range(61):
            c.action(obs[0])
            c.observe(obs[0])
        self.assertEqual(c.phase, "failed")
        self.assertEqual(c.monitor.reason, "settling_timeout")
        with self.assertRaises(ValueError):
            c.action(obs[0])


if __name__ == "__main__":
    unittest.main()
