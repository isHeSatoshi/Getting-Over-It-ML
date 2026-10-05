from copy import deepcopy
import gzip
import json
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import patch

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import torch

from research.fast_fidelity import NUMERIC, DISCRETE
from research.evaluation_cases import EvaluationCase
from research.goal_env import GoalEnv, GoalHistory, local_reward, relabel, schema
from research.goal_archive import (GoalArchive, WaypointSupervisor, compare_snapshot, digest,
                                  extend_chain, make_prefix, prefix_identity, replay_prefix, snapshot, waypoints)
from research.goal_curriculum import truncate_prefix
from research.goal_replay import GoalReplayBuffer
from research.goal_train import TickBudget, make_model, verify_checkpoint, train_seed, NEXT_RETURN_AND_EVALUATION_RESERVE


class MockBridge:
    def reset(self, seed):
        self.last_seed = seed
        return {}


class MockGoalRaw(gym.Env):
    pipeline_mock_only = True
    action_mode, frame_skip, terrain, horizon = "absolute", 1, object(), 2400
    observation_space = spaces.Box(-np.inf, np.inf, shape=(217,), dtype=np.float32)
    action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def __init__(self):
        self.bridge, self.state, self.pointer = MockBridge(), None, np.zeros(2)

    def _raw(self):
        raw = np.zeros(217, np.float32)
        raw[0:2] = [self.state["player_world_x"]/5500, self.state["player_world_y"]/16000]
        raw[13:15] = self.pointer/128
        raw[21:23] = 1
        raw[23] = .5
        raw[-128:] = np.arange(128, dtype=np.float32)/128
        return raw

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        game_seed = int(self.np_random.integers(0, 2**32))
        self.bridge.reset(game_seed)
        self.count = 0
        self.pointer[:] = 0
        self.state = {key: 0 for key in NUMERIC+DISCRETE}
        self.state.update(tick=120, frame_id=120, game_time=4., physics_hz=30, player_world_y=21,
            hammer_world_x=30, hammer_world_y=21, backend="turbowarp-real-renderer",
            body_collision=True, hammer_collision=False, success=False, dead=False, schema_version=2,
            stage_width=480, stage_height=360)
        return self._raw(), {"physics_ticks": 0}

    def step(self, applied):
        self.count += 1
        self.pointer = np.asarray(applied, np.float64)*128
        dx, dy = float(applied[0]), float(applied[1])
        self.state["player_world_x"] += dx
        self.state["player_world_y"] += dy
        self.state.update(tick=120+self.count, frame_id=120+self.count, command_id_applied=self.count,
            game_time=(120+self.count)/30, player_vx=dx, player_vy=dy, hammer_vx=dx, hammer_vy=dy,
            hammer_world_x=self.state["player_world_x"]+30, hammer_world_y=self.state["player_world_y"],
            pointer_x=float(self.pointer[0]), pointer_y=float(self.pointer[1]),
            dead=self.state["player_world_y"] < -180, success=self.state["player_world_y"] > 16000)
        terminal = bool(self.state["dead"] or self.state["success"])
        info = {"physics_ticks": 1, "dead": self.state["dead"], "success": self.state["success"],
                "retained_gain": self.state["player_world_y"]-21}
        return self._raw(), -.1, terminal, bool(self.count >= self.horizon and not terminal), info


def replay_transition(index, *, eligible=True, dead=False, terminal=False):
    bodies = np.asarray([[index+i, 21] for i in range(4)], np.float64)
    nxt = bodies+np.asarray([1, 0])
    zero = np.zeros(620, np.float32)
    return {"observation": relabel(zero, bodies, [100, 50]), "next_observation": relabel(zero, nxt, [100, 50]),
            "bodies": bodies, "next_bodies": nxt, "action": np.asarray([.2, .3], np.float32),
            "goal": np.asarray([100., 50.]), "achieved": nxt[-1], "speed": 1.,
            "eligible": eligible, "dead": dead, "terminal": terminal}


def prefix_fixture(length=4):
    env = GoalEnv(MockGoalRaw(), budget=TickBudget(maximum=10000))
    env.reset(seed=123)
    reset = snapshot(env)
    commands, route, histories = [], [], []
    chain = digest(reset)
    for _ in range(length):
        issued = np.asarray([.5, .25], np.float32)
        env.step_recorded(issued, issued)
        command = {"issued": issued.tolist(), "applied": issued.tolist()}
        history = snapshot(env)
        commands.append(command); route.append(history["state"]); histories.append(history)
        chain = extend_chain(chain, command, history["state"], history)
    record = make_prefix(env, commands, route, reset, {"mock_only": True}, chain=chain)
    record["snapshots"] = histories
    record["id"] = prefix_identity(record)
    return env, record


class GoalObservationTests(unittest.TestCase):
    def test_exact620_order_no_flags_reward_or_rms_and_causal_padding(self):
        raw = np.arange(217, dtype=np.float32)
        history = GoalHistory()
        history.reset(raw, [10, 20])
        obs = history.observation([160, 20]).reshape(4, 155)
        np.testing.assert_array_equal(obs[:, :21], np.repeat(raw[None, :21], 4, axis=0))
        self.assertEqual(obs[0, 21], raw[23])
        self.assertEqual(obs[0, 22], raw[24])
        np.testing.assert_array_equal(obs[0, 23:151], raw[-128:])
        np.testing.assert_array_equal(obs[0, 151:155], [1, 0, 0, 0])
        self.assertEqual(schema()["dimension"], 620)

    def test_goal_change_relabels_all_frames_but_keeps_actual_body_history_and_own_actions(self):
        history = GoalHistory()
        history.reset(np.zeros(217, np.float32), [0, 21])
        history.push(np.zeros(217, np.float32), [5, 25], np.asarray([.3, -.2], np.float32))
        obs = history.observation([30, 40]).reshape(4, 155)
        np.testing.assert_allclose(obs[-1, 151:153], np.asarray([25, 15])/150)
        np.testing.assert_array_equal(obs[-1, 153:], np.asarray([.3, -.2], np.float32))
        changed = history.observation([-10, 100]).reshape(4, 155)
        np.testing.assert_array_equal(changed[:, :151], obs[:, :151])
        np.testing.assert_array_equal(changed[:, 153:], obs[:, 153:])

    def test_dense_goal_reward_speed_and_death_are_reconstructable(self):
        self.assertEqual(local_reward([0, 0], [0, 0], 0, False), 1)
        self.assertAlmostEqual(local_reward([0, 0], [100, 0], 4, False), -1.1)
        self.assertEqual(local_reward([0, 0], [300, 0], 20, True), -12.5)

    def test_issued_not_applied_history_and_no_autoreset_at_suffix_end(self):
        env = GoalEnv(MockGoalRaw(), budget=TickBudget(maximum=10000))
        env.reset(seed=123); env.begin_suffix([100, 21])
        issued, applied = np.asarray([.3, .2], np.float32), np.asarray([-.5, .1], np.float32)
        obs, _, _, _, info = env.step_recorded(issued, applied, category="learner", eligible=False)
        np.testing.assert_array_equal(obs.reshape(4, 155)[-1, 153:], issued)
        np.testing.assert_array_equal(info["goal_transition"]["action"], issued)
        np.testing.assert_array_equal(info["goal_transition"]["applied"], applied)
        self.assertFalse(info["goal_transition"]["eligible"])
        env.suffix_steps = 599
        obs, _, terminal, truncated, _ = env.step(issued)
        self.assertTrue(truncated); self.assertFalse(terminal)
        self.assertEqual(obs.shape, (620,))
        with self.assertRaises(ValueError):
            env.step(issued)

    def test_budget_stops_before_reset_or_step(self):
        budget = TickBudget(maximum=120)
        env = GoalEnv(MockGoalRaw(), budget=budget)
        env.reset(seed=1)
        with self.assertRaisesRegex(ValueError, "budget"):
            env.step(np.zeros(2, np.float32))
        self.assertEqual(env.env.count, 0)
        self.assertEqual(NEXT_RETURN_AND_EVALUATION_RESERVE, 120+10*(120+3600)+2*(120+1800)+600)
        small = TickBudget(maximum=NEXT_RETURN_AND_EVALUATION_RESERVE-1)
        with self.assertRaises(ValueError):
            small.before(NEXT_RETURN_AND_EVALUATION_RESERVE)

    def test_nonfinite_goal_raw_and_illegal_controls_rejected(self):
        env = GoalEnv(MockGoalRaw())
        env.reset(seed=123)
        with self.assertRaises(ValueError):
            env.set_goal([np.nan, 0])
        with self.assertRaises(ValueError):
            env.step(np.asarray([2, 0], np.float32))


class GoalReplayTests(unittest.TestCase):
    def buffer(self, size=32):
        return GoalReplayBuffer(size, spaces.Box(-np.inf, np.inf, shape=(620,), dtype=np.float32),
                                spaces.Box(-1, 1, shape=(2,), dtype=np.float32))

    def test_forced_warmups_excluded_for_actor_critic_and_future_her(self):
        buffer = self.buffer()
        buffer.begin_suffix()
        for i in range(8):
            buffer.add_transition(replay_transition(i, eligible=i >= 4))
        batch = buffer.sample(64)
        np.testing.assert_array_equal(batch.actions.numpy(), np.repeat(np.asarray([[.2, .3]], np.float32), 64, axis=0))
        # All original and hindsight rewards correspond to eligible current frames.
        self.assertEqual(batch.observations.shape, (64, 620))

    def test_her_recomputes_every_current_and_next_historical_frame(self):
        buffer = self.buffer()
        buffer.begin_suffix()
        for i in range(8):
            buffer.add_transition(replay_transition(i))
        batch = buffer._get_samples(np.asarray([0]*20))
        changed = batch.observations.numpy().reshape(20, 4, 155)
        nxt = batch.next_observations.numpy().reshape(20, 4, 155)
        self.assertEqual(buffer.last_her_count, 10)
        for row in range(20):
            goal_x = float(changed[row, 0, 151])*150
            for frame in range(4):
                self.assertAlmostEqual(float(changed[row, frame, 151])*150, goal_x-frame, places=4)
                self.assertAlmostEqual(float(nxt[row, frame, 151])*150, goal_x-frame-1, places=4)
            np.testing.assert_array_equal(changed[row, :, 153:], 0)

    def test_death_her_excluded_but_original_transition_remains_terminal(self):
        buffer = self.buffer()
        buffer.begin_suffix()
        buffer.add_transition(replay_transition(0, dead=True, terminal=True))
        buffer.add_transition(replay_transition(1))
        batch = buffer._get_samples(np.asarray([0]*16))
        self.assertEqual(buffer.last_her_count, 0)
        np.testing.assert_array_equal(batch.dones.numpy(), 1)
        np.testing.assert_array_equal(batch.observations.numpy(), np.repeat(buffer.observations[0][None], 16, axis=0))

    def test_time_limit_bootstraps_and_future_goals_never_cross_suffix(self):
        buffer = self.buffer()
        buffer.begin_suffix(); buffer.add_transition(replay_transition(0))
        buffer.begin_suffix(); buffer.add_transition(replay_transition(20))
        batch = buffer._get_samples(np.asarray([0]*16))
        self.assertEqual(buffer.last_her_count, 0)
        np.testing.assert_array_equal(batch.dones.numpy(), 0)

    def test_ring_overwrite_and_checkpoint_preserve_sequence_and_rng(self):
        buffer = self.buffer(4)
        for episode in range(3):
            buffer.begin_suffix()
            for i in range(3):
                buffer.add_transition(replay_transition(i+episode*10))
        self.assertTrue(buffer.full)
        self.assertTrue(all(buffer.sequence[i] == serial for rows in buffer.episodes.values() for i, serial in rows))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"owned_replay.pkl.gz"
            buffer.save(path)
            with gzip.open(path, "rb") as stream:
                loaded = pickle.load(stream)  # Only this test's own generated checkpoint.
            np.testing.assert_array_equal(buffer.sample(8).observations.numpy(), loaded.sample(8).observations.numpy())

    def test_no_eligible_data_or_generic_autoreset_add_rejected(self):
        buffer = self.buffer()
        with self.assertRaises(ValueError):
            buffer.sample(2)
        with self.assertRaises(ValueError):
            buffer.add(None)


class GoalArchiveTests(unittest.TestCase):
    def test_nominal_prefix_replay_verifies_game_seed_endpoint_and_history(self):
        env, record = prefix_fixture()
        replay_prefix(env, record)
        compare_snapshot(snapshot(env), record["endpoint"])
        tampered = deepcopy(record)
        tampered["commands"][0]["applied"][0] += .01
        with self.assertRaisesRegex(ValueError, "integrity"):
            replay_prefix(env, tampered)

    def test_endpoint_drift_never_widens_tolerance(self):
        env, record = prefix_fixture()
        bad = deepcopy(record["endpoint"])
        bad["state"]["player_world_x"] += 1e-5
        with self.assertRaisesRegex(ValueError, "drift"):
            compare_snapshot(snapshot(env), bad)

    def test_route_truncation_keeps_actual_causal_endpoint(self):
        env, record = prefix_fixture(10)
        short = truncate_prefix(record, 4)
        replay_prefix(env, short)
        self.assertEqual(short["length"], 4)
        compare_snapshot(snapshot(env), record["snapshots"][3])

    def test_archive_caps_representatives_and_practice_count(self):
        env, record = prefix_fixture()
        archive = GoalArchive(maximum_cells=2)
        archive.add(record); archive.add(deepcopy(record))
        self.assertEqual(sum(len(rows) for rows in archive.cells.values()), 1)
        archive.launched(record["endpoint"]["state"])
        self.assertEqual(sum(archive.practice.values()), 1)
        selected = archive.choose(np.random.default_rng(1), under_practiced=True)
        self.assertEqual(selected["id"], record["id"])

    def test_transient_positions_never_become_stable_waypoints(self):
        _, record = prefix_fixture(100)
        route = record["route"]
        for row in route:
            row["player_vy"] = 3
        self.assertEqual(waypoints(route), [])
        for row in route:
            row.update(player_world_x=322, player_world_y=104, player_vx=0, player_vy=0)
        anchors = waypoints(route)
        self.assertTrue(anchors[0]["first_ledge"])
        self.assertEqual(anchors[-1]["index"], 99)

    def test_waypoint_hold_firstledge_gate_and_fall_recovery(self):
        targets = [{"xy": [322, 104], "first_ledge": True}, {"xy": [450, 180], "first_ledge": False}]
        supervisor = WaypointSupervisor(targets)
        state = {"player_world_x": 322, "player_world_y": 104, "player_vx": 0, "player_vy": 0}
        for _ in range(40):
            supervisor.observe(state, False)
        self.assertEqual(supervisor.target, 0)
        supervisor.observe(state, True)
        self.assertEqual(supervisor.target, 1)
        state["player_world_y"] = 60
        supervisor.observe(state, True)
        self.assertEqual(supervisor.target, 0)


class GoalModelTests(unittest.TestCase):
    def test_sac_settings_and_bounded_mock_update(self):
        model = make_model(21, 64)
        self.assertEqual(model.gamma, .995)
        self.assertEqual(model.policy.net_arch, [128, 128])
        self.assertEqual(model.target_entropy, -2)
        model.replay_buffer.begin_suffix()
        for i in range(32):
            model.replay_buffer.add_transition(replay_transition(i))
        from research.optimizer_work import OptimizerWork
        with OptimizerWork(model, "sac") as work:
            model.train(1, 16)
        self.assertEqual(work.summary()["optimizer_step_calls"],
                         {"actor": 1, "critic": 1, "entropy_temperature": 1})

    def test_complete_bounded_mock_curriculum_training_and_checkpoint(self):
        class ScaffoldMock(MockGoalRaw):
            def step(self, applied):
                observation, reward, terminal, truncated, info = super().step(applied)
                if self.count <= 600:
                    last = (self.state["player_world_x"], self.state["player_world_y"])
                    self.state["player_world_x"] = min(self.count, 400)*322/400
                    self.state["player_world_y"] = 21+min(self.count, 400)*83/400
                    self.state["player_vx"] = self.state["player_world_x"]-last[0]+float(applied[0])
                    self.state["player_vy"] = self.state["player_world_y"]-last[1]+float(applied[1])
                    self.state["hammer_world_x"] = self.state["player_world_x"]+30
                    self.state["hammer_world_y"] = self.state["player_world_y"]
                    observation = self._raw()
                return observation, reward, terminal, truncated, info
        env = GoalEnv(ScaffoldMock(), budget=TickBudget(maximum=10000))
        with tempfile.TemporaryDirectory() as folder:
            def forced_case(rng, reset_seed):
                return EvaluationCase("mock_left", reset_seed, ((-.75, -.125),)*3)
            with patch("research.goal_curriculum.perturbation", side_effect=forced_case):
                model, targets, report = train_seed(env, np.zeros((600, 2), np.float32), 21,
                    Path(folder)/"owned", guard=lambda: None, maximum=16, replay_capacity=64,
                    checkpoint_every=0, allow_mock=True)
            self.assertEqual(report["learner_transitions"], 16)
            self.assertEqual(model.replay_buffer.pos, 28)
            self.assertEqual(np.count_nonzero(model.replay_buffer.eligible), 16)
            self.assertEqual(report["physics"]["categories"]["forced_warmup"], 12)
            self.assertEqual(report["physics"]["categories"]["learner"], 16)
            self.assertEqual(report["sac_cycles"], 0)
            self.assertTrue(targets)
            path = Path(folder)/"owned"/report["checkpoint"]
            metadata = verify_checkpoint(path)
            self.assertEqual(metadata["step"], 16)
            self.assertEqual(metadata["schema"]["dimension"], 620)
            (path/"supervisor.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash"):
                verify_checkpoint(path)


if __name__ == "__main__":
    unittest.main()
