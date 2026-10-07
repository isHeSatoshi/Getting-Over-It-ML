"""Golden-trace gates for the accelerated original runtime, never training."""
import argparse
from datetime import datetime, timezone
import json
import math
import numpy as np

from research.browser_bridge import BrowserBridge, ROOT
from research.fast_bridge import FastBridge
from research.env import RealGettingOverItEnv
from research.provenance import fingerprint
from research.trajectory_search import commands_from_knots
from research.validate import validate

NUMERIC = (
    "tick", "frame_id", "game_time", "physics_hz", "player_world_x", "player_world_y",
    "player_vx", "player_vy", "player_impulse_vx", "player_impulse_vy", "hammer_world_x",
    "hammer_world_y", "hammer_vx", "hammer_vy", "hammer_angle_rad", "hammer_angular_velocity",
    "camera_x", "camera_y", "player_screen_x", "player_screen_y", "pointer_x", "pointer_y",
    "control_error_memory_x", "control_error_memory_y", "effort", "hammer_air", "last_tx",
    "last_ty", "last_hammer_distance", "last_effort", "offset_x", "offset_y", "collision_queries",
)
DISCRETE = ("schema_version", "backend", "body_collision", "hammer_collision", "success", "dead",
            "command_id_applied", "stage_width", "stage_height")


def compare(reference, fast, tolerance=1e-8):
    if len(reference) != len(fast):
        raise AssertionError(f"Different trajectory lengths: {len(reference)} vs {len(fast)}")
    errors = {key: 0.0 for key in NUMERIC}
    for index, (a, b) in enumerate(zip(reference, fast)):
        for key in DISCRETE:
            if a[key] != b[key]:
                raise AssertionError(f"Discrete mismatch at {index}: {key}")
        for key in NUMERIC:
            if not math.isfinite(a[key]) or not math.isfinite(b[key]):
                raise AssertionError(f"Non-finite telemetry at {index}: {key}")
            error = abs(a[key] - b[key])
            errors[key] = max(errors[key], error)
            if error > tolerance:
                raise AssertionError(f"Numeric mismatch at {index}: {key}, error={error}")
    return errors


def cases():
    rng = np.random.default_rng(0)
    result = {}
    for name, target in (("idle", (0, 0)), ("push_hold", (0, -80))):
        result[name] = [{"x": target[0], "y": target[1], "id": i + 1} for i in range(240)]
    for name, sign in (("clockwise_long", -1), ("counterclockwise_long", 1)):
        result[name] = [{"x": 90 * math.cos(sign * i * math.pi / 60),
                         "y": 90 * math.sin(sign * i * math.pi / 60), "id": i + 1} for i in range(1200)]
    result["abrupt_random"] = [
        {"x": float(a[0]), "y": float(a[1]), "id": 4 * i + j + 1}
        for i, a in enumerate(rng.uniform(-128, 128, (128, 2))) for j in range(4)]
    angles = -np.linspace(0, 359 * math.pi / 60, 19)
    knots = np.stack([90 * np.cos(angles), 90 * np.sin(angles)], axis=1)
    result["smooth_sweep_hold"] = commands_from_knots(knots, 360)
    result["smooth_sweep_hold"] += [{**result["smooth_sweep_hold"][-1], "id": i + 361} for i in range(240)]
    return result


def placement_expression(x, y):
    # Diagnostic only: not a legal training reset or demonstration of reaching
    # this region. Preserve the hammer/body displacement and centre the level.
    return f"""(()=>{{
        const vars=Object.values(vm.runtime.getTargetForStage().variables);
        const get=n=>vars.find(v=>v.name===n);
        const dx={x}-Number(get('PLAYER X').value),dy={y}-Number(get('PLAYER Y').value);
        for(const n of ['PLAYER X','HAMMER X'])get(n).value=Number(get(n).value)+dx;
        for(const n of ['PLAYER Y','HAMMER Y'])get(n).value=Number(get(n).value)+dy;
        get('CAMERA X').value={x};get('CAMERA Y').value=Math.max(0,{y});
        vm.runtime.startHats('event_whenbroadcastreceived',{{BROADCAST_OPTION:'centre'}});
        vm.runtime.startHats('event_whenbroadcastreceived',{{BROADCAST_OPTION:'Position Level'}});
        return true;
    }})()"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Use on a separate browser-test host")
    args = parser.parse_args()
    output = ROOT / "artifacts" / ("fast_fidelity_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    report = {"provenance": fingerprint(), "cases": {}, "limit": "Tested trajectories, not whole-game equivalence"}
    with BrowserBridge(driver="selenium", headless=args.headless) as reference, FastBridge(headless=args.headless) as fast:
        report["fast_control_validation"] = validate(fast)["checks"]
        for seed in (42, 1001):
            for name, commands in cases().items():
                a_start = reference.reset(seed)
                b_start = fast.reset(seed)
                compare([a_start], [b_start])
                a = reference.step_commands(commands)
                # Different RPC partitioning must not affect dynamics.
                b = []
                for i in range(0, len(commands), 37):
                    b.extend(fast.step_commands(commands[i:i + 37]))
                    if b and (b[-1]["dead"] or b[-1]["success"]):
                        break
                errors = compare(a, b)
                key = f"{name}_seed_{seed}"
                report["cases"][key] = {
                    "ticks": len(a), "max_error": max(errors.values()), "errors": errors,
                    "body_hit_ticks": sum(s["body_collision"] for s in a),
                    "hammer_hit_ticks": sum(s["hammer_collision"] for s in a),
                    "dead": a[-1]["dead"], "success": a[-1]["success"],
                    "collision_memo": fast.evaluate("research.stats()"),
                }
                (output / (key + ".json")).write_text(json.dumps({
                    "commands": commands[:len(a)], "reference": a, "fast": b}), encoding="utf-8")
                print(key, report["cases"][key]["ticks"], "ticks, max error", max(errors.values()), flush=True)
        for name, x, y in (("empty_water_death", -900, 21), ("upper_gravity_probe", 4000, 12100)):
            reference.reset(42); fast.reset(42)
            expression = placement_expression(x, y)
            reference.evaluate(expression); fast.evaluate(expression)
            commands = [{"x": 0, "y": 0, "id": i + 1} for i in range(120)]
            a = reference.step_commands(commands)
            b = fast.step_commands(commands)
            errors = compare(a, b)
            report["cases"][name] = {"diagnostic_placement": True, "ticks": len(a),
                                    "max_error": max(errors.values()), "dead": a[-1]["dead"],
                                    "body_hit_ticks": sum(s["body_collision"] for s in a),
                                    "hammer_hit_ticks": sum(s["hammer_collision"] for s in a)}
            (output / (name + ".json")).write_text(
                json.dumps({"reference": a, "fast": b}), encoding="utf-8")
            print(name, report["cases"][name], flush=True)
        # Includes observations and the rolling reward, not just body positions.
        for action_mode, action in (("absolute", (0, -0.625)), ("velocity", (0, -1)), ("polar", (1, 1))):
            a_env = RealGettingOverItEnv(bridge=reference, action_mode=action_mode, terrain=True, horizon=64)
            b_env = RealGettingOverItEnv(bridge=fast, action_mode=action_mode, terrain=True, horizon=64)
            a_obs, _ = a_env.reset(seed=42); b_obs, _ = b_env.reset(seed=42)
            assert np.allclose(a_obs, b_obs, rtol=0, atol=1e-6)
            for _ in range(64):
                a_obs, ar, at, ax, ai = a_env.step(action)
                b_obs, br, bt, bx, bi = b_env.step(action)
                assert (at, ax) == (bt, bx)
                assert np.allclose(a_obs, b_obs, rtol=0, atol=1e-6)
                assert math.isclose(ar, br, abs_tol=1e-10)
                if at or ax: break
            report["cases"]["environment_" + action_mode] = {"observations_rewards_outcomes_match": True}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Evidence:", output)


if __name__ == "__main__":
    main()
