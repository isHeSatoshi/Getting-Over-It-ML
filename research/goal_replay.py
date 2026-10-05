"""Dense bounded replay with sampled same-suffix HER and exact frame reconstruction."""
import gzip
import pickle
from pathlib import Path

import numpy as np
import torch
from stable_baselines3.common.buffers import BaseBuffer
from stable_baselines3.common.type_aliases import ReplayBufferSamples

from research.demonstrations import require
from research.goal_env import DIMENSION, local_reward, relabel


class GoalReplayBuffer(BaseBuffer):
    def __init__(self, buffer_size, observation_space, action_space, device="cpu", n_envs=1,
                 optimize_memory_usage=False, **kwargs):
        require(n_envs == 1 and observation_space.shape == (DIMENSION,) and not optimize_memory_usage,
                "Goal replay requires one620-feature simulator")
        super().__init__(buffer_size, observation_space, action_space, device=device, n_envs=1)
        self.observations = np.zeros((buffer_size, DIMENSION), np.float32)
        self.next_observations = np.zeros_like(self.observations)
        self.bodies = np.zeros((buffer_size, 4, 2), np.float64)
        self.next_bodies = np.zeros_like(self.bodies)
        self.actions = np.zeros((buffer_size, 2), np.float32)
        self.goals = np.zeros((buffer_size, 2), np.float64)
        self.achieved = np.zeros_like(self.goals)
        self.speeds = np.zeros(buffer_size, np.float64)
        self.dead = np.zeros(buffer_size, bool)
        self.terminal = np.zeros(buffer_size, bool)
        self.eligible = np.zeros(buffer_size, bool)
        self.episode = np.full(buffer_size, -1, np.int64)
        self.sequence = np.full(buffer_size, -1, np.int64)
        self.episodes = {}
        self.serial, self.episode_id, self.episode_step = 0, -1, 0
        self.rng = np.random.default_rng(0)
        self.last_her_count = 0

    def begin_suffix(self):
        self.episode_id += 1
        self.episode_step = 0
        self.episodes[self.episode_id] = []

    def add_transition(self, transition):
        require(self.episode_id >= 0, "Replay transition needs an actual suffix boundary")
        index = self.pos
        old = int(self.episode[index])
        if old in self.episodes:
            self.episodes[old] = [pair for pair in self.episodes[old] if pair[0] != index]
            if not self.episodes[old]:
                del self.episodes[old]
        fields = (("observations", "observation"), ("next_observations", "next_observation"),
                  ("bodies", "bodies"), ("next_bodies", "next_bodies"), ("actions", "action"),
                  ("goals", "goal"), ("achieved", "achieved"))
        for destination, source in fields:
            values = np.asarray(transition[source])
            require(values.shape == getattr(self, destination)[index].shape and np.isfinite(values).all(),
                    "Invalid replay transition shape/nonfinite data")
            getattr(self, destination)[index] = values
        require(np.abs(self.actions[index]).max() <= 1, "Replay stores the legal issued action")
        self.speeds[index] = transition["speed"]
        require(np.isfinite(self.speeds[index]) and self.speeds[index] >= 0,
                "Replay speed is invalid")
        for name in ("dead", "terminal", "eligible"):
            require(type(transition[name]) is bool, "Replay outcome/eligibility flags must be booleans")
            getattr(self, name)[index] = transition[name]
        self.episode[index], self.sequence[index] = self.episode_id, self.serial
        self.episodes.setdefault(self.episode_id, []).append((index, self.serial))
        self.serial += 1
        self.episode_step += 1
        self.pos = (self.pos+1) % self.buffer_size
        self.full |= self.pos == 0

    def add(self, *args, **kwargs):
        raise ValueError("Use actual goal suffix transitions, not generic VecEnv/autoreset replay")

    def _get_samples(self, batch_inds, env=None):
        require(env is None, "Goal replay must not use a running normalizer")
        obs = self.observations[batch_inds].copy()
        nxt = self.next_observations[batch_inds].copy()
        goals = self.goals[batch_inds].copy()
        slots = self.rng.choice(len(batch_inds), len(batch_inds)//2, replace=False)
        self.last_her_count = 0
        for slot in slots:
            index = int(batch_inds[slot])
            if self.dead[index] or not self.eligible[index]:
                continue
            candidates = [j for j, serial in self.episodes[int(self.episode[index])]
                          if serial > self.sequence[index] and not self.terminal[j] and self.eligible[j]]
            if candidates:
                future = int(self.rng.choice(candidates))
                goals[slot] = self.achieved[future]
                obs[slot] = relabel(obs[slot], self.bodies[index], goals[slot])
                nxt[slot] = relabel(nxt[slot], self.next_bodies[index], goals[slot])
                self.last_her_count += 1
        rewards = np.asarray([local_reward(self.achieved[index], goal, self.speeds[index],
                                          bool(self.dead[index]))
                              for index, goal in zip(batch_inds, goals)], np.float32)[:, None]
        return ReplayBufferSamples(observations=self.to_torch(obs), actions=self.to_torch(self.actions[batch_inds]),
            next_observations=self.to_torch(nxt), dones=self.to_torch(self.terminal[batch_inds, None].astype(np.float32)),
            rewards=self.to_torch(rewards))

    def sample(self, batch_size, env=None):
        size = self.buffer_size if self.full else self.pos
        indices = np.flatnonzero(self.eligible[:size])
        require(len(indices) > 0 and batch_size >= 1, "No eligible actor/critic transitions")
        selected = self.rng.choice(indices, size=batch_size, replace=True)
        return self._get_samples(selected, env)

    def save(self, path):
        path = Path(path)
        require(path.is_absolute() and not path.exists(), "Fresh owned replay checkpoint required")
        with gzip.open(path, "xb", compresslevel=1) as stream:
            pickle.dump(self, stream, protocol=pickle.HIGHEST_PROTOCOL)
