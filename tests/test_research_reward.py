"""Research reward invariants, including terminal and discounted-cycle exploits."""
import math
import unittest

from research.reward import ClimbReward, RewardConfig, PROFILES


def physical(y=21.0, vx=0.0, vy=0.0, contact=True):
    return {
        "player_world_y": y, "player_vx": vx, "player_vy": vy,
        "body_collision": contact, "hammer_collision": False,
        "success": y > 16000, "dead": y < -180,
    }


def roll(reward, sequence):
    result = []
    for state in sequence:
        result.append(reward.advance([state]))
    return result


class RewardContracts(unittest.TestCase):
    def reward(self, profile="settled", frame_skip=1):
        reward = ClimbReward(RewardConfig(profile=profile), frame_skip=frame_skip)
        reward.reset(physical())
        return reward

    def test_discount_matches_physical_half_life(self):
        config = RewardConfig()
        for skip in (1, 4, 8, 16):
            discount = config.gamma(skip)
            self.assertAlmostEqual(discount ** (120 * 30 / skip), 0.5)
        self.assertAlmostEqual(config.gamma(4), 0.9992301329658564)

    def test_idle_is_not_paid_in_any_profile(self):
        for profile in PROFILES:
            r = self.reward(profile)
            terms = roll(r, [physical()] * 120)
            self.assertTrue(all(t["potential_shaping"] == 0 for t in terms))
            self.assertTrue(all(t["reward_total"] < 0 for t in terms))

    def test_settled_height_beats_equal_peak_ballistic_jump_locally(self):
        jump, hold = self.reward(), self.reward()
        for _ in range(30):
            airborne = jump.advance([physical(y=121, vy=3, contact=False)])
            settled = hold.advance([physical(y=121)])
        self.assertEqual(airborne["settled_gain"], 0)
        self.assertEqual(settled["settled_gain"], 100)
        self.assertGreater(settled["reward_potential_after"], airborne["reward_potential_after"])
        # This is a shaping-feature comparison, not a different terminal task.

    def test_settled_height_is_rolling_minimum_not_a_maximum(self):
        reward = self.reward()
        for _ in range(30):
            reward.advance([physical(y=121)])
        terms = reward.advance([physical(y=71)])
        self.assertEqual(terms["settled_gain"], 50)
        for _ in range(30):
            terms = reward.advance([physical()])
        self.assertEqual(terms["settled_gain"], 0)
        self.assertEqual(terms["reward_potential_after"], 0)

    def test_airborne_or_fast_contact_cannot_certify_settled_progress(self):
        for state in (physical(y=121, contact=False), physical(y=121, vx=3), physical(y=121, vy=-3)):
            reward = self.reward()
            roll(reward, [state] * 90)
            self.assertEqual(reward.settled_gain, 0)

    def test_contacts_do_not_pay_without_height(self):
        reward = self.reward()
        terms = roll(reward, [physical(contact=(i % 2 == 0)) for i in range(90)])
        self.assertTrue(all(t["potential_shaping"] == 0 for t in terms))

    def test_discounted_cycles_cannot_farm_shaping(self):
        for profile in ("height", "settled"):
            reward = self.reward(profile)
            sequence = ([physical(y=121)] * 45 + [physical()] * 45) * 3
            terms = roll(reward, sequence)
            total = sum(reward.gamma ** i * t["potential_shaping"] for i, t in enumerate(terms))
            self.assertAlmostEqual(total, 0, places=11)
            self.assertLess(sum(reward.gamma ** i * t["reward_total"] for i, t in enumerate(terms)), 0)

    def test_below_spawn_waiting_cannot_earn_positive_shaping(self):
        reward = self.reward("height")
        terms = roll(reward, [physical(y=-100)] * 30)
        self.assertTrue(all(t["potential_shaping"] == 0 for t in terms))
        self.assertTrue(all(t["reward_total"] < 0 for t in terms))

    def test_progress_gradient_continues_past_first_400_units(self):
        reward = self.reward("height")
        potentials = []
        for gain in (0, 50, 400, 1000, 8000, 15979):
            reward.advance([physical(y=21 + gain)])
            potentials.append(reward.height_potential)
        self.assertTrue(all(b > a for a, b in zip(potentials, potentials[1:])))
        self.assertAlmostEqual(potentials[-1], reward.config.potential_budget)

    def test_ongoing_plateau_does_not_pay_a_recurring_hold_bonus(self):
        reward = self.reward()
        roll(reward, [physical(y=121)] * 45)
        terms = reward.advance([physical(y=121)])
        self.assertLess(terms["potential_shaping"], 0)
        self.assertLess(terms["reward_total"], 0)

    def test_terminal_zeroes_potential_and_shaping_does_not_change_task_return(self):
        for terminal in (physical(y=-181), physical(y=16001)):
            returns = []
            for profile in PROFILES:
                reward = self.reward(profile)
                terms = roll(reward, [physical(y=121)] * 45 + [terminal])
                self.assertEqual(terms[-1]["reward_potential_after"], 0)
                discounted_shaping = sum(reward.gamma ** i * t["potential_shaping"] for i, t in enumerate(terms))
                self.assertAlmostEqual(discounted_shaping, 0, places=11)
                returns.append(sum(reward.gamma ** i * t["reward_total"] for i, t in enumerate(terms)))
                with self.assertRaises(RuntimeError):
                    reward.advance([physical()])
            self.assertAlmostEqual(returns[0], returns[1], places=11)
            self.assertAlmostEqual(returns[1], returns[2], places=11)

    def test_time_limit_keeps_nonterminal_potential(self):
        reward = self.reward("height")
        terms = reward.advance([physical(y=121)])
        self.assertGreater(terms["reward_potential_after"], 0)
        # Env truncation must keep this state and bootstrap; no reset is paid.
        discounted = terms["potential_shaping"]
        self.assertAlmostEqual(discounted, reward.gamma * reward.height_potential)
        reward.reset(physical())
        self.assertEqual(reward.height_potential, 0)
        self.assertEqual(reward.settled_gain, 0)

    def test_suicide_is_not_preferred_just_to_avoid_clock_cost(self):
        config = RewardConfig()
        for skip in (1, 4, 16):
            self.assertLess(config.describe(skip)["discounted_idle_cost_bound"], config.death_penalty)

    def test_invalid_states_and_configs_fail(self):
        for kwargs in ({"profile": "contacts"}, {"discount_half_life_seconds": math.nan},
                       {"physics_hz": 0}, {"death_penalty": 0.01}, {"airborne_weight": 1.1},
                       {"settled_window_seconds": 1e-5}, {"discount_half_life_seconds": 1e30}):
            with self.assertRaises(ValueError):
                RewardConfig(**kwargs)
        reward = self.reward()
        with self.assertRaises(ValueError):
            reward.advance([{**physical(), "success": True}])
        reward.reset(physical())
        with self.assertRaises(ValueError):
            reward.advance([physical(y=math.nan)])
        reward = self.reward(frame_skip=4)
        with self.assertRaises(ValueError):
            reward.advance([physical()])
        with self.assertRaises(ValueError):
            reward.advance([physical(y=-181), physical()])

    def test_invalid_trace_does_not_mutate_reward_history(self):
        reward = self.reward(frame_skip=4)
        before = reward.observation()
        with self.assertRaises(ValueError):
            reward.advance([physical(y=121), physical(y=math.nan), physical(), physical()])
        self.assertEqual(reward.observation(), before)


if __name__ == "__main__":
    unittest.main()
