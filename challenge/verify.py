"""Prove the runtime is the real one before anyone trusts a number.

Run this first. If it fails, scores from this machine are not comparable.
"""
import argparse
import json
import math
import sys


def check_reset(bridge):
    state = bridge.reset(1001)
    problems = []
    if state["backend"] != "turbowarp-real-renderer":
        problems.append(f"unexpected backend {state['backend']!r}")
    if state["schema_version"] != 2:
        problems.append(f"unexpected schema {state['schema_version']!r}")
    if not 15.0 <= state["player_world_y"] <= 30.0:
        problems.append(f"did not settle on start terrain: Y={state['player_world_y']}")
    if not state["body_collision"]:
        problems.append("no body contact at spawn")
    if state["collision_queries"] == 0:
        problems.append("renderer performed no collision queries")
    return problems, {"spawn_y": state["player_world_y"],
                      "backend": state["backend"]}


def check_clock(bridge):
    """Ticks must advance one frame at a time on a 30 Hz virtual clock."""
    problems = []
    trace = bridge.step_commands(
        [{"x": 0.0, "y": -128.0, "id": i + 1} for i in range(120)])
    if len(trace) != 120:
        problems.append(f"expected 120 ticks, got {len(trace)}")
    for previous, current in zip(trace, trace[1:]):
        if current["tick"] != previous["tick"] + 1:
            problems.append(f"tick desync {previous['tick']}->{current['tick']}")
            break
        if current["frame_id"] != previous["frame_id"] + 1:
            problems.append(f"frame desync {previous['frame_id']}->{current['frame_id']}")
            break
        step = current["game_time"] - previous["game_time"]
        if not math.isclose(step, 1.0 / current["physics_hz"], abs_tol=1e-9):
            problems.append(f"clock step {step} is not one physics tick")
            break
    return problems, {"final_y": trace[-1]["player_world_y"] if trace else None}


def check_control(bridge):
    """The documented causal test: a downward push must raise the body."""
    problems = []
    bridge.reset(1001)
    start = bridge.read_state()["player_world_y"]
    trace = bridge.step_commands(
        [{"x": 0.0, "y": -128.0, "id": i + 1} for i in range(120)])
    end = trace[-1]["player_world_y"]
    if end <= start:
        problems.append(f"downward push did not raise the body: {start} -> {end}")
    if not 50.0 <= end <= 140.0:
        problems.append(f"push landed outside the measured range: {end}")
    return problems, {"start_y": start, "end_y": end, "gain": end - start}


def check_idle(bridge):
    """An idle agent must not gain height. This is the no-credit control."""
    problems = []
    bridge.reset(1001)
    trace = bridge.step_commands(
        [{"x": 0.0, "y": 0.0, "id": i + 1} for i in range(120)])
    start = trace[0]["player_world_y"]
    end = trace[-1]["player_world_y"]
    if abs(end - start) > 5.0:
        problems.append(f"idle drifted by {end - start:.2f} units")
    return problems, {"start_y": start, "end_y": end}


CHECKS = (check_reset, check_clock, check_control, check_idle)


def run(backend="reference", driver="selenium"):
    from research.backends import make_bridge
    report = {}
    failed = []
    with make_bridge(backend, driver) as bridge:
        for check in CHECKS:
            name = check.__name__.replace("check_", "")
            try:
                problems, detail = check(bridge)
            except Exception as error:
                problems, detail = [f"{type(error).__name__}: {error}"], {}
            report[name] = {"passed": not problems, "problems": problems, **detail}
            if problems:
                failed.append(name)
    return {"backend": backend, "checks": report, "failed": failed,
            "ok": not failed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="reference", choices=("reference", "fast"))
    parser.add_argument("--driver", default="selenium")
    args = parser.parse_args()
    report = run(args.backend, args.driver)
    for name, result in report["checks"].items():
        status = "PASS" if result["passed"] else "FAIL"
        detail = {k: v for k, v in result.items()
                  if k not in ("passed", "problems")}
        print(f"[{status}] {name} {json.dumps(detail)}")
        for problem in result["problems"]:
            print(f"        - {problem}")
    print()
    print("Runtime verified." if report["ok"] else "RUNTIME VERIFICATION FAILED.")
    sys.exit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
