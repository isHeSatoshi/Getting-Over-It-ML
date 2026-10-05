"""Hash-bound legal-prefix archive and stable waypoint supervision, never teleportation."""
from collections import deque
from copy import deepcopy
import hashlib
import gzip
import json
import math
from pathlib import Path

import numpy as np

from research.demonstrations import require
from research.fast_fidelity import NUMERIC, DISCRETE
from research.goal_env import GoalHistory, action
from research.goal_study import MAX_PREFIX


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def prefix_identity(record):
    return digest({key: value for key, value in record.items()
                   if key not in ("id", "commands", "route", "snapshots")})


def extend_chain(previous, command, state, history):
    return digest({"previous": previous, "command": command, "state": state, "history": history})


def copy_prefix(record):
    # Immutable per-tick records are shared; lists and endpoint metadata are
    # copied. This avoids O(prefix*620) deepcopy on every learner transition.
    return {**record, "commands": list(record["commands"]), "route": list(record["route"]),
            "snapshots": list(record.get("snapshots", [])), "endpoint": deepcopy(record["endpoint"])}


def snapshot(env):
    return {"state": {key: env.env.state[key] for key in NUMERIC+DISCRETE},
            "raw": env.raw.tolist(), "frames": np.asarray(env.history.frames).tolist(),
            "bodies": env.history.body_history().tolist()}


def cell(state):
    octant = int(math.floor((state["hammer_angle_rad"] % (2*math.pi))/(math.pi/4))) % 8
    return f'{math.floor(state["player_world_x"]/25)}:{math.floor(state["player_world_y"]/25)}:{octant}'


def body(state):
    return np.asarray([state["player_world_x"], state["player_world_y"]], np.float64)


def offset(record):
    s = record["endpoint"]["state"]
    return np.asarray([s["hammer_world_x"]-s["player_world_x"], s["hammer_world_y"]-s["player_world_y"]])


def stable_score(route):
    if len(route) < 90:
        return None
    tail = route[-90:]
    if any(math.hypot(s["player_vx"], s["player_vy"]) > 2 or s["dead"] or s["success"] for s in tail):
        return None
    return min(s["player_world_y"] for s in tail)


def make_prefix(env, commands, route, reset_snapshot, provenance, parent=None, perturbation=None, chain=None):
    require(len(commands) == len(route) and len(commands) <= MAX_PREFIX, "Prefix cap/trajectory mismatch")
    record = {"reset_seed": env.reset_seed, "game_seed": env.game_seed, "commands": list(commands),
              "route": list(route), "reset": reset_snapshot, "endpoint": snapshot(env),
              "provenance": provenance, "parent": parent, "perturbation": perturbation,
              "score": stable_score(route), "chain": chain or digest(reset_snapshot), "length": len(commands)}
    record["id"] = prefix_identity(record)
    return record


def compare_snapshot(actual, expected):
    require(actual["state"].keys() == expected["state"].keys(), "Prefix telemetry schema changed")
    for key in DISCRETE:
        require(actual["state"][key] == expected["state"][key], f"Prefix discrete drift: {key}")
    for key in NUMERIC:
        require(math.isclose(actual["state"][key], expected["state"][key], rel_tol=0, abs_tol=1e-7),
                f"Prefix physical drift: {key}")
    for key, tolerance in (("raw", 1e-6), ("frames", 1e-6), ("bodies", 1e-7)):
        a, b = np.asarray(actual[key]), np.asarray(expected[key])
        require(a.shape == b.shape and np.isfinite(a).all()
                and np.allclose(a, b, rtol=0, atol=tolerance), f"Prefix observation/history drift: {key}")


def replay_prefix(env, record, *, clock=None):
    identifier = record["id"]
    require(identifier == prefix_identity(record),
            "Prefix content hash changed")
    chain = digest(record["reset"])
    require(len(record["commands"]) == len(record["route"]) == len(record["snapshots"]) == record["length"],
            "Prefix causal trajectory length changed")
    for command, state, history in zip(record["commands"], record["route"], record["snapshots"]):
        chain = extend_chain(chain, command, state, history)
    require(chain == record["chain"], "Prefix step-chain integrity failed")
    env.reset(seed=record["reset_seed"])
    require(env.game_seed == record["game_seed"], "Actual game reset seed changed")
    compare_snapshot(snapshot(env), record["reset"])
    commands, route = [], []
    for tick, command in enumerate(record["commands"]):
        issued = np.asarray(command["issued"], np.float32)
        nominal_applied = np.asarray(command["applied"], np.float32)
        applied = nominal_applied if clock is None else clock.apply(nominal_applied[None, :], tick)[0]
        _, _, terminal, truncated, _ = env.step_recorded(issued, applied, category="prefix")
        commands.append({"issued": issued.tolist(), "applied": applied.tolist()})
        route.append({key: env.env.state[key] for key in NUMERIC+DISCRETE})
        if terminal or truncated:
            require(clock is not None, "Verified nominal prefix became terminal")
            return commands, route, False
    if clock is None:
        compare_snapshot(snapshot(env), record["endpoint"])
    return commands, route, True


def waypoints(route):
    anchors, last, first_ledge = [], None, False
    for index, s in enumerate(route):
        if index < 29:
            continue
        point = body(s)
        recent = route[index-29:index+1]
        stable = all(np.linalg.norm(body(row)-point) <= 12
                     and math.hypot(row["player_vx"], row["player_vy"]) <= 2
                     and not row["dead"] and not row["success"] for row in recent)
        if not stable or np.linalg.norm(point-[0, 21]) <= 12:
            continue
        # Cast explicitly: comparisons against numpy coordinates yield
        # np.bool_, which standard json.dumps cannot serialize when the
        # supervisor/checkpoint writes these anchors.
        central = bool(305 <= point[0] <= 335 and 100 <= point[1] <= 112)
        forced = bool(central and not first_ledge)
        if forced or last is None or np.linalg.norm(point-last) >= 25:
            anchors.append({"xy": point.tolist(), "index": index, "first_ledge": forced})
            last = point
        first_ledge |= central
    if route and len(route) >= 30:
        s, point = route[-1], body(route[-1])
        if all(np.linalg.norm(body(row)-point) <= 12 and math.hypot(row["player_vx"], row["player_vy"]) <= 2
               and not row["dead"] and not row["success"] for row in route[-30:]):
            if np.linalg.norm(point-[0, 21]) > 12 and (not anchors or anchors[-1]["index"] != len(route)-1):
                anchors.append({"xy": point.tolist(), "index": len(route)-1,
                                "first_ledge": bool(not first_ledge
                                                    and 305 <= point[0] <= 335 and 100 <= point[1] <= 112)})
    return anchors


class GoalArchive:
    def __init__(self, maximum_cells=256):
        require(type(maximum_cells) is int and 2 <= maximum_cells <= 256, "Invalid pilot archive cap")
        self.maximum_cells, self.cells, self.practice = maximum_cells, {}, {}
        self.best = None
        self.spawn_cell = None

    def add(self, record):
        require(len(record["commands"]) <= MAX_PREFIX and record["id"] == prefix_identity(record),
                "Invalid archived legal prefix")
        key = cell(record["endpoint"]["state"])
        if not record["commands"]:
            self.spawn_cell = key
        score = record["score"]
        if score is not None and (self.best is None or
                (-score, len(record["commands"]), record["id"]) <
                (-self.best["score"], len(self.best["commands"]), self.best["id"])):
            self.best = copy_prefix(record)
        if key not in self.cells and len(self.cells) >= self.maximum_cells:
            protected = {self.spawn_cell, cell(self.best["endpoint"]["state"]) if self.best else None}
            candidates = [item for item in self.cells if item not in protected]
            require(candidates, "No unprotected archive cell available")
            victim = min(candidates, key=lambda k: (-self.practice.get(k, 0),
                max(row["score"] if row["score"] is not None else row["endpoint"]["state"]["player_world_y"]
                    for row in self.cells[k]), k))
            del self.cells[victim]
            self.practice.pop(victim, None)
        rows = {row["id"]: row for row in self.cells.get(key, [])}
        rows[record["id"]] = copy_prefix(record)
        shortest = min(rows.values(), key=lambda row: (len(row["commands"]), row["id"]))
        others = [row for row in rows.values() if row["id"] != shortest["id"]]
        chosen = [shortest]
        if others:
            chosen.append(min(others, key=lambda row: (
                -float(np.linalg.norm(offset(row)-offset(shortest))), len(row["commands"]), row["id"])))
        self.cells[key] = chosen
        self.practice.setdefault(key, 0)

    def choose(self, rng, under_practiced=False):
        keys = sorted(self.cells)
        require(keys, "Archive empty")
        if under_practiced:
            count = min(self.practice[key] for key in keys)
            keys = [key for key in keys if self.practice[key] == count]
        key = keys[int(rng.integers(len(keys)))]
        return copy_prefix(self.cells[key][int(rng.integers(len(self.cells[key])))])

    def launched(self, state):
        key = cell(state)
        self.practice[key] = self.practice.get(key, 0)+1

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)
        records = {row["id"]: row for rows in self.cells.values() for row in rows}
        if self.best:
            records[self.best["id"]] = self.best
        for identifier, record in records.items():
            with gzip.open(directory/f"{identifier}.json.gz", "xt", compresslevel=1) as stream:
                json.dump(record, stream, separators=(",", ":"), allow_nan=False)
        manifest = {"version": "legal-prefix-archive-v1", "cells": {
            key: [row["id"] for row in rows] for key, rows in self.cells.items()},
            "practice": self.practice, "spawn_cell": self.spawn_cell, "best": self.best["id"] if self.best else None,
            "maximum_cells": self.maximum_cells}
        (directory/"manifest.json").write_text(json.dumps(manifest, indent=2))
        return manifest


class WaypointSupervisor:
    def __init__(self, targets):
        require(len(targets) > 0, "No stable deployment waypoints")
        self.targets = deepcopy(targets)
        self.target, self.completed, self.hold = 0, -1, 0
        self.recovering = False
        self.recovery_limit = None

    def goal(self):
        return np.asarray(self.targets[self.target]["xy"], np.float64)

    def observe(self, state, first_ledge_held=False):
        point = body(state)
        speed = math.hypot(state["player_vx"], state["player_vy"])
        if self.completed >= 0 and point[1] < min(
                self.targets[self.completed]["xy"][1], self.goal()[1])-30:
            if not self.recovering:
                self.recovery_limit = max(0, min(self.completed, self.target-1))
            choices = range(self.recovery_limit+1)
            self.target = min(choices, key=lambda i: (float(np.linalg.norm(point-self.targets[i]["xy"])), -i))
            self.hold, self.recovering = 0, True
        self.hold = self.hold+1 if np.linalg.norm(point-self.goal()) <= 12 and speed <= 2 else 0
        first_ok = not self.targets[self.target]["first_ledge"] or first_ledge_held
        if self.hold >= 30 and first_ok:
            self.completed = self.target
            if self.target+1 < len(self.targets):
                self.target += 1
            self.hold, self.recovering = 0, False
            self.recovery_limit = None
        return self.goal()
