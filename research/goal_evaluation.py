"""Continuous learned reference play, without prefix/action playback."""
from copy import deepcopy
import json
import math
from pathlib import Path

import numpy as np

from research.demonstrations import require
from research.case_clock import PhysicalCaseClock
from research.env import RealGettingOverItEnv
from research.fast_fidelity import NUMERIC, DISCRETE
from research.goal_archive import WaypointSupervisor
from research.goal_env import GoalEnv, GoalHistory, schema
from research.goal_study import CASES, plan
from research.study_metrics import enable_platform_support


def evaluate(model, bridge, targets, budget, output, *, guard=lambda: None, cases=CASES, ticks=3600):
    require(model.observation_space.shape == (620,) and 1 <= ticks <= 3600,
            "Saved actor schema/evaluation budget mismatch")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for case in cases:
        guard()
        raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True,
                                  frame_skip=1, horizon=ticks)
        enable_platform_support(raw)
        env = GoalEnv(raw, budget=budget)
        supervisor = WaypointSupervisor(targets)
        env.reset(seed=case.reset_seed)
        reset_raw = env.raw.tolist()
        reset_state = {key: raw.state[key] for key in NUMERIC+DISCRETE}
        observation = env.set_goal(supervisor.goal())
        clock, sustained, achieved_height = PhysicalCaseClock(case), 0, False
        path = output/f"{case.name}.jsonl"
        final = None
        with path.open("x") as stream:
            for tick in range(ticks):
                guard()
                issued = model.predict(observation, deterministic=True)[0].astype(np.float32)
                applied = clock.apply(issued[None, :], tick)[0]
                observation, reward, terminal, truncated, info = env.step_recorded(
                    issued, applied, category="evaluation", eligible=False)
                state = {key: raw.state[key] for key in NUMERIC+DISCRETE}
                speed = math.hypot(state["player_vx"], state["player_vy"])
                qualified = state["player_world_y"] >= 180 and speed <= 2 and not info["dead"]
                sustained = sustained+1 if qualified else 0
                achieved_height |= sustained >= 90
                previous_goal = supervisor.goal().tolist()
                next_goal = supervisor.observe(state, info["milestone_success"]["first_ledge_v1"])
                observation = env.set_goal(next_goal)
                transition = info.pop("goal_transition")
                row = {"tick": tick+1, "case": case.name, "issued": issued.tolist(), "applied": applied.tolist(),
                       "goal": previous_goal, "next_goal": next_goal.tolist(),
                       "observation": transition["observation"].tolist(),
                       "next_observation_before_goal_switch": transition["next_observation"].tolist(),
                       "raw_pre": transition["raw_pre"].tolist(), "raw_post": transition["raw_post"].tolist(),
                       "reward_local": reward, "reward_climb_v2": transition["original_reward"],
                       "state": state, "info": info, "terminal": terminal, "truncated": truncated,
                       "height180_hold90": achieved_height, "teacher_prefix_used": False}
                stream.write(json.dumps(row, separators=(",", ":"), allow_nan=False)+"\n")
                final = row
                if terminal or truncated:
                    break
        env.close()
        records.append({"case": json.loads(json.dumps(case.describe())), "ticks": final["tick"],
                        "first_ledge": bool(final["info"]["milestone_success"]["first_ledge_v1"]),
                        "height180_hold90": achieved_height, "retained_gain": final["info"]["retained_gain"],
                        "dead": final["info"]["dead"], "summit": final["info"]["success"],
                        "trace": path.name, "prefix_used": False, "reset_raw": reset_raw,
                        "reset_state": reset_state, "actual_game_seed": env.game_seed})
    result = {"version": "goal-continuous-reference-v1", "backend": "reference", "schema": schema(),
              "records": records, "nominal_first_ledge": records[0]["first_ledge"],
              "first_ledge_successes": sum(row["first_ledge"] for row in records),
              "nominal_height180_hold90": records[0]["height180_hold90"],
              "deaths": sum(row["dead"] for row in records), "summits": sum(row["summit"] for row in records),
              "all_evaluations_learned_only": True,
              "pilot_gate_passed": bool(records[0]["first_ledge"] and
                  sum(row["first_ledge"] for row in records) >= 8 and records[0]["height180_hold90"]),
              "final_goal_verified": False}
    (output/"evaluation.json").write_text(json.dumps(result, indent=2))
    return result


def validate_evaluation(directory, expected_cases=CASES):
    """Reconstruct the new-height and unchanged first-ledge gates from raw states."""
    from research.milestones import MilestoneTracker, FIRST_LEDGE
    from research.timing_probe import PLATFORM_SUPPORT
    from research.goal_archive import WaypointSupervisor
    from research.goal_env import local_reward
    directory = Path(directory)
    summary = json.loads((directory/"evaluation.json").read_text())
    require(summary["backend"] == "reference" and summary["schema"] == schema()
            and len(summary["records"]) == len(expected_cases), "Changed scored evaluation/schema")
    targets = json.loads((directory.parent/"supervisor.json").read_text())["waypoints"]
    for result, case in zip(summary["records"], expected_cases):
        require(result["case"] == json.loads(json.dumps(case.describe())) and result["prefix_used"] is False
                and result["trace"] == f"{case.name}.jsonl", "Changed evaluation case or playback flag")
        rows = [json.loads(line) for line in (directory/result["trace"]).read_text().splitlines()]
        require(1 <= len(rows) == result["ticks"] <= 3600, "Incomplete evaluation trace")
        tracker = MilestoneTracker((FIRST_LEDGE, PLATFORM_SUPPORT), physics_hz=30)
        supervisor, clock = WaypointSupervisor(targets), PhysicalCaseClock(case)
        initial = result["reset_state"]
        require(initial["tick"] == 120 and initial["player_world_x"] == 0 and initial["player_world_y"] == 21,
                "Scored policy did not start on ordinary terrain")
        history = GoalHistory()
        history.reset(np.asarray(result["reset_raw"], np.float32), [0, 21])
        hold, passed, previous = 0, False, None
        for index, row in enumerate(rows):
            s = row["state"]
            require(row["teacher_prefix_used"] is False and row["tick"] == index+1
                    and s["tick"] == s["frame_id"] == 121+index and s["command_id_applied"] == index+1,
                    "Evaluation prefix/physics/control clock violation")
            require(s["success"] == (s["player_world_y"] > 16000) and s["dead"] == (s["player_world_y"] < -180),
                    "Original summit/death mismatch")
            if previous is not None:
                require(all(math.isclose(s[f"{prefix}_v{axis}"],
                    s[f"{prefix}_world_{axis}"]-previous[f"{prefix}_world_{axis}"], rel_tol=0, abs_tol=1e-7)
                    for prefix in ("player", "hammer") for axis in ("x", "y")), "Velocity/physical position drift")
            require(row["goal"] == supervisor.goal().tolist(), "Unexpected goal supervisor/action scaffold")
            require(np.array_equal(np.asarray(row["observation"], np.float32), history.observation(supervisor.goal())),
                    "Scored actor input is not actual causal history")
            applied = clock.apply(np.asarray([row["issued"]], np.float32), index)[0].tolist()
            require(applied == row["applied"] and len(row["observation"]) == 620,
                    "Evaluation actuation/history mismatch")
            raw_post = np.asarray(row["raw_post"], np.float32)
            require(raw_post[0] == np.float32(s["player_world_x"]/5500)
                    and raw_post[1] == np.float32(s["player_world_y"]/16000)
                    and raw_post[2] == np.float32(s["player_vx"]/64)
                    and raw_post[3] == np.float32(s["player_vy"]/64),
                    "Policy telemetry contradicts physical body movement")
            history.push(raw_post, [s["player_world_x"], s["player_world_y"]], np.asarray(row["issued"], np.float32))
            require(np.array_equal(np.asarray(row["next_observation_before_goal_switch"], np.float32),
                                   history.observation(supervisor.goal())),
                    "Scored next input/history or issued action differs")
            tracker.advance([s])
            require(row["info"]["milestone_success"] == tracker.summary()["milestone_success"],
                    "Reported first-ledge hold differs from actual physical trace")
            speed = math.hypot(s["player_vx"], s["player_vy"])
            hold = hold+1 if s["player_world_y"] >= 180 and speed <= 2 and not s["dead"] else 0
            passed |= hold >= 90
            require(row["height180_hold90"] == passed, "Incorrect90tick retained-height gate")
            goal = supervisor.observe(s, tracker.summary()["milestone_success"]["first_ledge_v1"]).tolist()
            require(row["next_goal"] == goal, "Goal advancement/recovery drift")
            require(row["terminal"] == bool(s["dead"] or s["success"])
                    and (not row["terminal"] or index == len(rows)-1), "Invalid terminal trace boundary")
            previous = s
        last = rows[-1]
        require(last["terminal"] or len(rows) == 3600, "Early nonterminal scored stopping")
        require(result["first_ledge"] == tracker.summary()["milestone_success"]["first_ledge_v1"]
                and result["height180_hold90"] == passed and result["dead"] == last["state"]["dead"]
                and result["summit"] == last["state"]["success"]
                and math.isclose(result["retained_gain"], last["state"]["player_world_y"]-21, abs_tol=1e-7),
                "Summary differs from scored physical outcome")
    nominal = summary["records"][0]
    expected = nominal["first_ledge"] and nominal["height180_hold90"] and sum(r["first_ledge"] for r in summary["records"]) >= 8
    require(summary["pilot_gate_passed"] == expected and summary["final_goal_verified"] is False,
            "Pilot/full-goal promotion mismatch")
    return summary
