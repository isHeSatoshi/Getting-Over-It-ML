"""Bounded CPU SAC/HER training with legal prefix curriculum; no automatic resume."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import random
import time

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import torch
from stable_baselines3 import SAC
from stable_baselines3.common.logger import configure

from research.demonstrations import require
from research.goal_env import GoalEnv, schema
from research.goal_replay import GoalReplayBuffer
from research.goal_curriculum import LegalCurriculum
from research.goal_archive import waypoints
from research.goal_study import MAX_LEARNER, MAX_PHYSICS, MAX_CYCLES, plan
from research.optimizer_work import OptimizerWork
from research.provenance import fingerprint

NEXT_RETURN_AND_EVALUATION_RESERVE = 120+10*(120+3600)+2*(120+1800)+600

def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(2**20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TickBudget:
    def __init__(self, maximum=MAX_PHYSICS, initial=None):
        require(type(maximum) is int and 0 < maximum <= MAX_PHYSICS, "Invalid total physics cap")
        self.maximum = maximum
        self.counts = deepcopy(initial or {})
        require(all(type(value) is int and value >= 0 for value in self.counts.values()), "Invalid previous allocation")
        self.before(0)

    @property
    def total(self):
        return sum(self.counts.values())

    def before(self, ticks):
        require(type(ticks) is int and ticks >= 0 and self.total+ticks <= self.maximum,
                "Total physics budget exhausted; no extension or extra reset")

    def add(self, category, ticks):
        self.before(ticks)
        self.counts[category] = self.counts.get(category, 0)+ticks

    def record(self):
        return {"maximum": self.maximum, "total": self.total, "categories": deepcopy(self.counts)}


class SpacesOnly(gym.Env):
    observation_space = spaces.Box(-np.inf, np.inf, shape=(620,), dtype=np.float32)
    action_space = spaces.Box(-1, 1, shape=(2,), dtype=np.float32)

    def reset(self, **kwargs):
        raise RuntimeError("SAC setup environment cannot simulate physics")

    def step(self, action):
        raise RuntimeError("Use the recorded legal curriculum, not generic SAC.learn")


def make_model(seed, replay_capacity=300000):
    require(type(replay_capacity) is int and 32 <= replay_capacity <= 300000, "Invalid replay cap")
    torch.set_num_threads(1)
    model = SAC("MlpPolicy", SpacesOnly(), seed=seed, device="cpu", learning_rate=.0003,
                buffer_size=replay_capacity, learning_starts=4096, batch_size=256, tau=.005,
                gamma=.995, train_freq=(2, "step"), gradient_steps=1, ent_coef="auto",
                target_entropy=-2, policy_kwargs={"net_arch": [128, 128], "activation_fn": torch.nn.ReLU},
                replay_buffer_class=GoalReplayBuffer)
    model.set_logger(configure(None, []))
    model.replay_buffer.rng = np.random.default_rng(seed+700000)
    return model


def checkpoint(model, curriculum, budget, output, step, optimizer_counts, rng):
    target = Path(output)/f"checkpoint_{step}"
    target.mkdir(parents=True, exist_ok=False)
    model.save(target/"model.zip")
    model.replay_buffer.save(target/"replay.pkl.gz")
    curriculum.archive.save(target/"archive")
    targets = waypoints(curriculum.archive.best["route"]) if curriculum.archive.best else []
    (target/"supervisor.json").write_text(json.dumps({"version": "stable-waypoint-v1", "waypoints": targets}, indent=2))
    with gzip.open(target/"rng.pkl.gz", "xb") as stream:
        pickle.dump({"numpy": np.random.get_state(), "python": random.getstate(),
                     "torch": torch.get_rng_state(), "curriculum": rng.bit_generator.state,
                     "replay": model.replay_buffer.rng.bit_generator.state}, stream)
    files = {path.relative_to(target).as_posix(): {
        "bytes": path.stat().st_size, "sha256": file_sha(path)}
        for path in target.rglob("*") if path.is_file()}
    manifest = {"version": "goal-checkpoint-v1", "step": step, "plan": plan(), "schema": schema(),
                "provenance": fingerprint(), "physics": budget.record(),
                "optimizer_counts": optimizer_counts, "files": files,
                "standalone_replay_requires_actual_reset": True, "resume_authorized": False}
    (target/"manifest.json").write_text(json.dumps(manifest, indent=2))
    return target


def train_seed(env, opening_actions, seed, output, *, guard, maximum=MAX_LEARNER,
               replay_capacity=300000, checkpoint_every=40000, allow_mock=False,
               demo=None, demo_burst_start=0.0, demo_burst_ticks=0):
    require(type(maximum) is int and 1 <= maximum <= MAX_LEARNER,
            "Invalid bounded learner transitions")
    if demo is not None:
        require(type(demo_burst_start) is float and 0 < demo_burst_start <= .05
                and type(demo_burst_ticks) is int and 1 <= demo_burst_ticks <= 600,
                "Demo seeding needs bounded burst settings")
    else:
        require(demo_burst_start == 0.0 and demo_burst_ticks == 0,
                "Demo burst settings require the state-matched matcher")
    if allow_mock:
        require(getattr(env.env, "pipeline_mock_only", False) and not hasattr(env.env.bridge, "driver"),
                "Mock optimizer test cannot use original game")
    else:
        guard()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    curriculum = LegalCurriculum(env, seed, fingerprint())
    curriculum.seed_opening(opening_actions)
    model = make_model(seed, replay_capacity)
    rng, step, cycles = np.random.default_rng(seed+300000), 0, 0
    last_checkpoint = None
    stop_reason = "learner_limit"
    demo_seed_learner = 0
    with OptimizerWork(model, "sac") as work:
        while step < maximum:
            guard()
            # Reserve one full evaluation before another legal return, so a cap
            # cannot leave a nominal-only scored result.
            if not allow_mock and env.budget.total+NEXT_RETURN_AND_EVALUATION_RESERVE > env.budget.maximum:
                stop_reason = "physics_reserve"
                break
            session = curriculum.start()
            if session is None:
                continue
            demo_burst = 0
            model.replay_buffer.begin_suffix()
            observation = session["observation"]
            while env.active and step < maximum:
                guard()
                elapsed = env.suffix_steps
                warmup = len(session["case"].warmup)*4
                eligible = elapsed >= warmup
                seeded = False
                if demo is not None and eligible:
                    if demo_burst > 0:
                        candidate, _ = demo.seed_action(env.raw)
                        if candidate is None:
                            demo_burst = 0
                        else:
                            issued, seeded, demo_burst = candidate, True, demo_burst-1
                    if not seeded and demo_burst <= 0 and rng.random() < demo_burst_start:
                        candidate, _ = demo.seed_action(env.raw)
                        if candidate is not None:
                            issued, seeded, demo_burst = candidate, True, demo_burst_ticks-1
                if not seeded:
                    if step < 4096:
                        issued = rng.uniform(-1, 1, 2).astype(np.float32)
                    else:
                        issued = model.predict(observation, deterministic=False)[0].astype(np.float32)
                applied = session["clock"].apply(issued[None, :], elapsed)[0]
                observation, reward, terminal, truncated, info = env.step_recorded(
                    issued, applied, category="learner" if eligible else "forced_warmup", eligible=eligible)
                transition = info["goal_transition"]
                model.replay_buffer.add_transition(transition)
                curriculum.retain(session, transition)
                step += int(eligible)
                demo_seed_learner += int(seeded)
                model.num_timesteps = step
                if eligible and step > 4096 and (step-4096) % 2 == 0:
                    require(cycles < MAX_CYCLES, "SAC update-cycle budget exhausted")
                    require(np.count_nonzero(model.replay_buffer.eligible) >= 1, "No valid learner experiences")
                    model.train(gradient_steps=1, batch_size=256)
                    cycles += 1
                with (output/"training_trace.jsonl").open("a") as stream:
                    if (eligible and step % 256 == 0) or terminal or truncated:
                        stream.write(json.dumps({"step": step, "cycles": cycles, "physics": env.budget.record(),
                            "issued": issued.tolist(), "applied": applied.tolist(), "goal": session["goal"].tolist(),
                            "body": transition["achieved"].tolist(), "reward_local": reward,
                            "reward_climb_v2": transition["original_reward"], "eligible": transition["eligible"],
                            "demo_seeded": seeded},
                            separators=(",", ":"), allow_nan=False)+"\n")
                if eligible and checkpoint_every and step % checkpoint_every == 0:
                    last_checkpoint = checkpoint(model, curriculum, env.budget, output, step, work.summary(), curriculum.rng)
                if terminal or truncated:
                    break
        counts = work.summary()
        require(0 <= step <= maximum and cycles == max(0, (step-4096)//2)
                and cycles <= MAX_CYCLES and model._n_updates == cycles,
                "Incomplete/excess SAC work")
        require(counts["optimizer_step_calls"] == {"actor": cycles, "critic": cycles, "entropy_temperature": cycles},
                "Actual optimizer callbacks differ from SAC cycles")
        if last_checkpoint is None or last_checkpoint.name != f"checkpoint_{step}":
            last_checkpoint = checkpoint(model, curriculum, env.budget, output, step, counts, curriculum.rng)
    targets = waypoints(curriculum.archive.best["route"])
    require(targets, "No stable deployment goal route")
    summary = {"version": "goal-training-v1", "seed": seed, "complete": step == maximum,
               "stop_reason": stop_reason,
               "learner_transitions": step, "sac_cycles": cycles, "optimizer": counts,
               "demo_seed_learner_transitions": demo_seed_learner,
               "demo_burst_start": demo_burst_start, "demo_burst_ticks": demo_burst_ticks,
               "physics": env.budget.record(), "checkpoint": last_checkpoint.name,
               "shared_scaffold_only": True, "teacher_actions_in_evaluation": False,
               "plan": plan(), "schema": schema()}
    (output/"training_summary.json").write_text(json.dumps(summary, indent=2))
    return model, targets, summary


def verify_checkpoint(directory):
    directory = Path(directory)
    manifest = json.loads((directory/"manifest.json").read_text())
    require(manifest["plan"] == plan() and manifest["schema"] == schema(), "Saved goal checkpoint schema mismatch")
    for name, spec in manifest["files"].items():
        path = directory/name
        require(path.resolve().is_relative_to(directory.resolve()) and path.is_file() and not path.is_symlink()
                and path.stat().st_size == spec["bytes"] and file_sha(path) == spec["sha256"],
                "Goal checkpoint file/hash mismatch")
    return manifest
