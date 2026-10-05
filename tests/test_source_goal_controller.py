import unittest

import numpy as np

from research.source_goal_controller import SourceGoalController, contract
from research.stroke_controller import StrokeController
from tests.test_hammer_target import raw


def fixture():
    pre = raw()
    observations = np.repeat(pre[None, :], 600, axis=0)
    observations[300] = raw(hammer=(187., 4.))
    actions = np.zeros((600, 2), np.float32)
    actions[300] = [.25, -.25]
    return observations, actions


def prefix(controller, pre):
    for _ in range(299):
        controller.action(pre)
        controller.observe(pre)


class SourceGoalTests(unittest.TestCase):
    def test_contract_has_one_state_checkpoint_and_no_oracle(self):
        record = contract()
        self.assertEqual((record["checkpoint_after_observed_steps"], record["maximum_decisions"]), (299, 751))
        self.assertFalse(record["case_seed_trace_oracle"])
        self.assertTrue(record["missed_checkpoint_permanent_bypass"])

    def test_nominal_unplanted_checkpoint_bypasses_exact_forever(self):
        obs, actions = fixture()
        pre = obs[0]
        wrapper, base = SourceGoalController(obs, actions), StrokeController(obs, actions, "contact_timed_feedback")
        for _ in range(350):
            np.testing.assert_array_equal(wrapper.action(pre), base.action(pre))
            wrapper.observe(pre)
        self.assertEqual(wrapper.phase, "bypass")
        planted = pre.copy()
        planted[22] = 1
        wrapper.action(pre)
        wrapper.observe(planted)
        wrapper.action(planted)
        self.assertFalse(wrapper.attempted)

    def test_goal_consumes_one_source_proposal_then_freezes_and_resumes_next(self):
        obs, actions = fixture()
        pre = obs[0].copy()
        pre[22] = 1
        wrapper = SourceGoalController(obs, actions)
        prefix(wrapper, pre)
        action = wrapper.action(pre)
        self.assertIsNotNone(wrapper.last["base_proposed_action"])
        post = pre.copy()
        post[13:15] = action
        wrapper.observe(post)
        self.assertEqual((wrapper.base.calls, wrapper.base.phase), (300, 299))
        action = wrapper.action(post)
        self.assertIsNone(wrapper.last["base_proposed_action"])
        self.assertEqual(wrapper.base.calls, 300)
        reached = raw(hammer=wrapper.goal)
        reached[13:15] = action
        wrapper.observe(reached)
        self.assertEqual(wrapper.phase, "resumed")
        wrapper.action(reached)
        self.assertEqual((wrapper.base.calls, wrapper.base.phase), (301, 300))
        wrapper.observe(reached)
        self.assertTrue(wrapper.attempted)
        self.assertEqual(wrapper.target.steps, 2)

    def test_other_trigger_conditions_and_exacttravel3_bypass(self):
        obs, actions = fixture()
        for travel, hammer, body in ((3., (190., -8.), (270., 32.)),
                                     (0., (187., 4.), (270., 32.)),
                                     (0., (190., -8.), (1000., 32.))):
            pre = raw(body=body, hammer=hammer)
            pre[22], pre[19] = 1, travel/64
            wrapper = SourceGoalController(obs, actions)
            prefix(wrapper, pre)
            wrapper.action(pre)
            self.assertEqual(wrapper.phase, "bypass")

    def test_target_timeout_is_terminal_and_never_rearms(self):
        obs, actions = fixture()
        pre = obs[0].copy()
        pre[22] = 1
        wrapper = SourceGoalController(obs, actions)
        prefix(wrapper, pre)
        for _ in range(30):
            action = wrapper.action(pre)
            post = pre.copy()
            post[13:15] = action
            wrapper.observe(post)
            pre = post
        self.assertEqual(wrapper.phase, "failed")
        self.assertEqual(wrapper.target.reason, "target_timeout")
        self.assertEqual(wrapper.base.calls, 300)
        with self.assertRaises(ValueError):
            wrapper.action(pre)

    def test_pair_prepost_and_rawquery_guards(self):
        obs, actions = fixture()
        wrapper = SourceGoalController(obs, actions)
        pre = obs[0]
        with self.assertRaises(ValueError):
            wrapper.observe(pre)
        wrapper.action(pre)
        with self.assertRaises(ValueError):
            wrapper.action(pre)
        wrapper.observe(pre)
        for invalid in (raw(body=(269., 32.)), pre.astype(np.float64)):
            with self.assertRaises(ValueError):
                wrapper.action(invalid)
        wrapper.reset()
        invalid = pre.copy()
        invalid[22] = .5
        with self.assertRaises(ValueError):
            wrapper.action(invalid)
        invalid[22], invalid[19] = 1, -1
        with self.assertRaises(ValueError):
            wrapper.action(invalid)

    def test_budget_and_reset_clear_own_command_and_attempt(self):
        obs, actions = fixture()
        wrapper = SourceGoalController(obs, actions)
        wrapper.executed = 751
        with self.assertRaises(ValueError):
            wrapper.action(obs[0])
        wrapper.reset()
        self.assertEqual(wrapper.executed, 0)
        self.assertIsNone(wrapper.issued_command)
        self.assertIsNone(wrapper.target)
        self.assertFalse(wrapper.attempted)


if __name__ == "__main__":
    unittest.main()
