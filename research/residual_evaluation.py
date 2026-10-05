"""Direct Gym reference residual evaluation with exact causal trace validation."""
from copy import deepcopy
import json
import math

import numpy as np

from research.case_clock import PhysicalCaseClock
from research.demonstrations import require
from research.env import RealGettingOverItEnv
from research.fast_fidelity import NUMERIC, DISCRETE
from research.milestones import MilestoneTracker, FIRST_LEDGE
from research.residual_controller import contract as scaffold_contract, validate_normalizer
from research.residual_env import ResidualGettingOverItEnv
from research.residual_study import CASES
from research.reward import DEATH_Y, SUCCESS_Y
from research.study_metrics import benchmark_contract, enable_platform_support
from research.timing_probe import PLATFORM_SUPPORT


def evaluate(policy, normalization, bridge, prior, actions, *, zero_actor=False, guard=lambda: None):
    require(type(zero_actor) is bool, "Explicit zero-actor evaluation flag required")
    validate_normalizer(normalization.obs_rms, scaffold_contract())
    snapshot = {key: np.asarray(getattr(normalization.obs_rms, key)).copy() for key in ("mean", "var", "count")}
    records = []
    for case in CASES:
        guard()
        raw_env = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True, frame_skip=1, horizon=1800)
        enable_platform_support(raw_env)
        env = ResidualGettingOverItEnv(raw_env, prior, actions, case=case)
        context, _ = env.reset(seed=case.reset_seed)
        reset_ticks, trace = raw_env.state["tick"], []
        try:
            for tick in range(1800):
                guard()
                actor_pre = context.copy()
                if zero_actor:
                    residual = np.zeros(2, np.float32)
                else:
                    residual = policy.predict(normalization.normalize_obs(context), deterministic=True)[0].astype(np.float32)
                context, reward, terminal, truncated, info = env.step(residual)
                observed = info.pop("residual_transition")
                row = {**info, "action": observed["last_transition"]["final_issued"],
                       "applied_action": observed["last_transition"]["actual_applied"],
                       "residual": residual.tolist(), "actor_input": actor_pre.tolist(),
                       "next_actor_input": context.tolist(), "transition": observed,
                       "reward": float(reward), "terminated": terminal, "truncated": truncated,
                       "state": {key: raw_env.state[key] for key in NUMERIC+DISCRETE}}
                trace.append(row)
                if terminal or truncated:
                    break
        finally:
            env.close()
        records.append({"case": json.loads(json.dumps(case.describe())), "seed": case.reset_seed, "trace": trace,
                        "final": trace[-1], "decisions": len(trace),
                        "controlled_physics_ticks": len(trace), "reset_settling_physics_ticks": reset_ticks})
    require(all(np.array_equal(snapshot[key], getattr(normalization.obs_rms, key)) for key in snapshot),
            "Evaluation updated training RMS")
    return records


def summarize(records, *, zero_actor=False):
    require(type(zero_actor) is bool and len(records) == 9
            and [row["case"]["name"] for row in records] == [case.name for case in CASES],
            "Missing/changed/duplicate ordered reference cases")
    holds = {metric["name"]: 0 for metric in benchmark_contract(True)}
    retained, completions, deaths, total = [], 0, 0, 0
    nominal_completion = nominal_hold = False
    for case, record in zip(CASES, records):
        require(record["case"] == json.loads(json.dumps(case.describe())) and record["seed"] == case.reset_seed,
                "Changed reference perturbation contract")
        trace = record["trace"]
        require(type(record["decisions"]) is int and 1 <= len(trace) == record["decisions"] <= 1800
                and record["final"] == trace[-1] and record["controlled_physics_ticks"] == len(trace)
                and record["reset_settling_physics_ticks"] == 120, "Invalid direct-Gym trace/reset accounting")
        clock = PhysicalCaseClock(case)
        tracker = MilestoneTracker((FIRST_LEDGE, PLATFORM_SUPPORT), physics_hz=30)
        tracker.reset()
        previous, last_raw = [0., 0.], None
        last_state = None
        for tick, row in enumerate(trace):
            state, transition = row["state"], row["transition"]["last_transition"]
            require(row["physics_ticks"] == 1 and state["tick"] == state["frame_id"] == 121+tick,
                    "Evaluation source/game clock mismatch")
            require(state["command_id_applied"] == tick+1
                    and all(math.isfinite(state[key]) for key in NUMERIC)
                    and state["physics_hz"] == 30, "Invalid physics telemetry/command acknowledgement")
            if last_state is not None:
                require(all(math.isclose(state[f"{name}_v{axis}"],
                    state[f"{name}_world_{axis}"]-last_state[f"{name}_world_{axis}"],
                    rel_tol=0, abs_tol=1e-7) for name in ("player", "hammer") for axis in ("x", "y")),
                    "Velocity disagrees with actual physical displacement")
            require(row["backend"] == state["backend"] == "turbowarp-real-renderer"
                    and row["milestone_contract"] == benchmark_contract(True), "Changed physics/hold gates")
            y = state["player_world_y"]
            require(math.isfinite(y) and type(state["success"]) is bool and type(state["dead"]) is bool
                    and state["success"] == (y > SUCCESS_Y) and state["dead"] == (y < DEATH_Y)
                    and row["success"] == state["success"] and row["dead"] == state["dead"],
                    "Completion/death contradicts original physical height")
            require(type(row["terminated"]) is bool and type(row["truncated"]) is bool
                    and row["terminated"] == bool(row["success"] or row["dead"])
                    and row["truncated"] == (tick+1 == 1800 and not row["terminated"])
                    and (not row["terminated"] or tick+1 == len(trace)), "Bad original terminal boundary")
            expected = transition["pre_observation"]+[float(np.float32(min(tick, 599)/599))]+transition["base_proposal"]+previous
            require(row["actor_input"] == transition["actor_input"] == expected
                    and len(expected) == 222 and all(math.isfinite(x) for x in expected)
                    and (last_raw is None or transition["pre_observation"] == last_raw),
                    "Actor pre-input/source/own memory is not causal")
            residual, base = np.asarray(row["residual"], np.float32), np.asarray(transition["base_proposal"], np.float32)
            require(residual.shape == (2,) and base.shape == (2,) and np.isfinite(residual).all()
                    and np.isfinite(base).all() and np.abs(residual).max() <= 1 and np.abs(base).max() <= 1,
                    "Invalid legal residual/base proposal")
            final = np.clip(base+np.float32(2)*residual, -1, 1).astype(np.float32).tolist()
            require(row["action"] == transition["final_issued"] == final
                    and transition["legal_residual"] == row["residual"]
                    and (not zero_actor or row["residual"] == [0., 0.]), "Wrong final residual actuation")
            applied = clock.apply(np.asarray([final], np.float32), tick)[0].tolist()
            require(row["applied_action"] == transition["actual_applied"] == applied,
                    "Actual controls differ from declared external physical clock")
            require(row["transition"]["steps"] == row["transition"]["base_calls"] == tick+1
                    and transition["source_phase"] == min(tick, 599)
                    and len(row["next_actor_input"]) == 222
                    and row["next_actor_input"][217] == float(np.float32(min(tick+1, 599)/599))
                    and row["next_actor_input"][:217] == transition["actual_post"]
                    and row["next_actor_input"][220:] == final, "Source/actual post history mismatch")
            post = np.asarray(transition["actual_post"], np.float32)
            require(post.shape == (217,) and np.isfinite(post).all()
                    and post[0] == np.float32(state["player_world_x"]/5500)
                    and post[1] == np.float32(y/16000)
                    and row["player_world_x"] == state["player_world_x"]
                    and row["player_world_y"] == y and row["body_hit_frames"] == int(state["body_collision"]),
                    "Raw policy post-input contradicts physical body telemetry")
            tracker.advance([state])
            physical = tracker.summary()
            require(row["milestone_success"] == physical["milestone_success"]
                    and row["milestone_success_seconds"] == physical["milestone_success_seconds"],
                    "Reported holds disagree with actual trace geometry/speed/contact")
            require(math.isfinite(row["retained_gain"])
                    and math.isclose(row["retained_gain"], y-21, rel_tol=0, abs_tol=1e-7),
                    "Retained gain changed ordinary spawn origin")
            previous, last_raw, last_state = final, transition["actual_post"], state
        last = trace[-1]
        require(last["success"] or last["dead"] or len(trace) == 1800, "Early nonterminal reference stopping")
        for name in holds:
            holds[name] += int(last["milestone_success"][name])
        completions += int(last["success"])
        deaths += int(last["dead"])
        retained.append(last["retained_gain"])
        total += len(trace)
        if case.name == "nominal":
            nominal_completion, nominal_hold = last["success"], last["milestone_success"]["first_ledge_v1"]
    return {"cases": 9, "holds": holds, "hold_rates": {key: value/9 for key, value in holds.items()},
            "full_completions": completions, "full_completion_rate": completions/9,
            "nominal_full_completion": nominal_completion, "nominal_central_hold": nominal_hold,
            "deaths": deaths, "median_retained_gain": sorted(retained)[4],
            "controlled_physics_ticks": total, "reset_settling_physics_ticks": 1080}
