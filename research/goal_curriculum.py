"""Actual legal return-to-state curriculum; prefixes never become learner labels."""
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.demonstrations import require
from research.evaluation_cases import EvaluationCase
from research.fast_fidelity import NUMERIC, DISCRETE
from research.goal_archive import (GoalArchive, body, digest, make_prefix, replay_prefix,
                                   snapshot, stable_score, waypoints, cell, extend_chain,
                                   prefix_identity, copy_prefix)
from research.goal_env import xy
from research.goal_study import MAX_PREFIX


def perturbation(rng, reset_seed):
    kind = int(rng.integers(4))
    seed = int(rng.integers(1, 2**31))
    case = (EvaluationCase("train_nominal", reset_seed), EvaluationCase("train_left", reset_seed, ((-.75, -.125),)*3),
            EvaluationCase("train_right", reset_seed, ((.75, -.125),)*3),
            EvaluationCase("train_noise", reset_seed, action_noise_std=.02, noise_seed=seed))[kind]
    return case


def truncate_prefix(record, length):
    require(0 <= length <= len(record["commands"]), "Invalid best-route replay point")
    # Every prefix endpoint has a causal observation/history snapshot. Route
    # positions alone are not sufficient to restore or validate a prefix.
    require("snapshots" in record and len(record["snapshots"]) == len(record["commands"]),
            "Best route has no endpoint history")
    result = copy_prefix(record)
    result["commands"] = result["commands"][:length]
    result["route"] = result["route"][:length]
    result["snapshots"] = result["snapshots"][:length]
    result["endpoint"] = deepcopy(result["reset"] if length == 0 else result["snapshots"][-1])
    result["score"] = stable_score(result["route"])
    result["parent"] = record["id"]
    result["length"] = length
    result["chain"] = digest(result["reset"])
    for command, state, history in zip(result["commands"], result["route"], result["snapshots"]):
        result["chain"] = extend_chain(result["chain"], command, state, history)
    result["id"] = prefix_identity(result)
    return result


class LegalCurriculum:
    def __init__(self, env, seed, provenance):
        self.env, self.rng = env, np.random.default_rng(seed)
        self.provenance = provenance
        self.archive = GoalArchive()

    def record(self, commands, route, snapshots, reset, parent=None, case=None, chain=None):
        record = make_prefix(self.env, commands, route, reset, self.provenance, parent,
                             None if case is None else json.loads(json.dumps(case.describe())), chain)
        record["snapshots"] = list(snapshots)
        record["id"] = prefix_identity(record)
        return record

    def seed_opening(self, actions, reset_seed=6001):
        """Legal historical opening actions, never learned evaluation or replay labels."""
        require(np.asarray(actions).shape == (600, 2), "Expected hash-validated historical opening")
        self.env.reset(seed=reset_seed)
        reset = snapshot(self.env)
        commands, route, snapshots = [], [], []
        chain = digest(reset)
        spawn = self.record(commands, route, snapshots, reset)
        self.archive.add(spawn)
        for issued in actions:
            _, _, terminal, truncated, _ = self.env.step_recorded(issued, issued, category="scaffold")
            require(not terminal and not truncated, "Historical opening scaffolding failed")
            commands.append({"issued": issued.tolist(), "applied": issued.tolist()})
            route.append({key: self.env.env.state[key] for key in NUMERIC+DISCRETE})
            snapshots.append(snapshot(self.env))
            chain = extend_chain(chain, commands[-1], route[-1], snapshots[-1])
            candidate = self.record(commands, route, snapshots, reset, chain=chain)
            self.archive.add(candidate)
        require(self.archive.best is not None and self.archive.best["score"] >= 100
                and len(waypoints(self.archive.best["route"])) > 0, "No stable opening scaffold route")

    def start(self):
        draw = float(self.rng.random())
        if draw < .4:
            selected = next(copy_prefix(rows[0]) for key, rows in self.archive.cells.items()
                            if key == self.archive.spawn_cell)
        elif draw < .8 and self.archive.best:
            selected = truncate_prefix(self.archive.best, int(self.rng.integers(len(self.archive.best["commands"])+1)))
        else:
            selected = self.archive.choose(self.rng, under_practiced=True)
        require(len(selected["commands"]) <= MAX_PREFIX, "Selected prefix exceeds pilot cap")
        case = perturbation(self.rng, selected["reset_seed"])
        # Always verify the nominal record first. A second, perturbed legal reset
        # deliberately creates a different actual state and counts all work.
        commands, route, valid = replay_prefix(self.env, selected)
        require(valid, "Verified nominal replay unexpectedly stopped")
        snapshots = list(selected["snapshots"])
        reset = deepcopy(selected["reset"])
        if case.warmup or case.action_noise_std:
            self.env.reset(seed=selected["reset_seed"])
            require(self.env.game_seed == selected["game_seed"], "Perturbed prefix reset seed changed")
            reset = snapshot(self.env)
            commands, route, snapshots = [], [], []
            chain = digest(reset)
            clock = PhysicalCaseClock(case)
            for tick, command in enumerate(selected["commands"]):
                issued = np.asarray(command["issued"], np.float32)
                applied = clock.apply(np.asarray([command["applied"]], np.float32), tick)[0]
                _, _, terminal, truncated, _ = self.env.step_recorded(issued, applied, category="prefix")
                commands.append({"issued": issued.tolist(), "applied": applied.tolist()})
                route.append({key: self.env.env.state[key] for key in NUMERIC+DISCRETE})
                snapshots.append(snapshot(self.env))
                chain = extend_chain(chain, commands[-1], route[-1], snapshots[-1])
                if terminal or truncated:
                    return None
            actual = self.record(commands, route, snapshots, reset, selected["id"], case, chain)
            self.archive.add(actual)
        else:
            chain = selected["chain"]
            self.archive.add(selected)
        self.archive.launched(self.env.env.state)
        goal = self.choose_goal()
        observation = self.env.begin_suffix(goal)
        # Suffix perturbations have a new causal physical clock. Forced-warmup
        # transitions remain recorded but ineligible for actor/critic/HER.
        suffix_case = perturbation(self.rng, selected["reset_seed"])
        return {"observation": observation, "goal": goal, "clock": PhysicalCaseClock(suffix_case),
                "case": suffix_case, "commands": commands, "route": route, "snapshots": snapshots,
                "reset": reset, "parent": selected["id"], "chain": chain}

    def choose_goal(self):
        actual = self.env.body
        draw = float(self.rng.random())
        if draw < .5 and self.archive.best:
            route = waypoints(self.archive.best["route"])
            if route:
                nearest = min(range(len(route)), key=lambda i: float(np.linalg.norm(actual-route[i]["xy"])))
                selected = min(nearest+1, len(route)-1) if self.rng.random() < .75 else int(self.rng.integers(len(route)))
                return xy(route[selected]["xy"])
        if draw < .75:
            known = [body(row["endpoint"]["state"]) for rows in self.archive.cells.values() for row in rows
                     if np.linalg.norm(body(row["endpoint"]["state"])-actual) <= 150]
            if known:
                return known[int(self.rng.integers(len(known)))]
        return actual+np.asarray([self.rng.uniform(-150, 150), self.rng.uniform(-50, 150)])

    def retain(self, session, transition):
        session["commands"].append({"issued": transition["action"].tolist(), "applied": transition["applied"].tolist()})
        session["route"].append({key: self.env.env.state[key] for key in NUMERIC+DISCRETE})
        session["snapshots"].append(snapshot(self.env))
        session["chain"] = extend_chain(session["chain"], session["commands"][-1],
                                       session["route"][-1], session["snapshots"][-1])
        if len(session["commands"]) <= MAX_PREFIX and not transition["terminal"]:
            candidate = self.record(session["commands"], session["route"], session["snapshots"],
                                    session["reset"], session["parent"], session["case"], session["chain"])
            self.archive.add(candidate)
