"""Causal, repeatability, frame, and renderer/terrain checks against the real game."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from research.browser_bridge import BrowserBridge, ROOT
from research.terrain import TerrainMap

PHYSICAL = (
    "tick", "frame_id", "player_world_x", "player_world_y", "hammer_world_x",
    "hammer_world_y", "player_vx", "player_vy", "hammer_vx", "hammer_vy",
    "body_collision", "hammer_collision", "camera_x", "camera_y",
)


def project_trace(trace):
    return [[s[k] for k in PHYSICAL] for s in trace]


def validate(bridge):
    checks = {}
    metadata = bridge.evaluate("window.research.metadata()")
    start = bridge.reset(42)
    assert start["player_world_y"] == 21 and start["body_collision"]
    checks["spawn_y"] = start["player_world_y"]
    idle = bridge.step_commands([{"x": 0, "y": 0, "id": i + 1} for i in range(60)])
    assert all(s["player_world_y"] == 21 and not s["dead"] for s in idle)
    checks["idle_body_range"] = 0
    # Direction probes establish pointer -> hammer response, not merely an ACK.
    responses = {}
    for name, x, y in [("right", 90, 0), ("left", -90, 0), ("up", 0, 80), ("down", 0, -80)]:
        bridge.reset(42)
        trace = bridge.step_commands([{"x": x, "y": y, "id": i + 1} for i in range(45)])
        s = trace[-1]
        responses[name] = [s["hammer_world_x"] - s["player_world_x"],
                           s["hammer_world_y"] - s["player_world_y"],
                           s["player_world_y"] - 21]
    assert responses["right"][0] > 50 and responses["left"][0] < -50
    assert responses["up"][1] > 90
    assert responses["down"][2] > 10 and responses["down"][1] < -10
    checks["direction_responses"] = responses
    commands = [{"x": 90 * math.cos(-i * math.pi / 60),
                 "y": 90 * math.sin(-i * math.pi / 60), "id": i + 1} for i in range(120)]
    start = bridge.reset(42)
    a = bridge.step_commands(commands)
    bridge.reset(42)
    b = []
    # Partitioning cannot change the simulated elapsed time or dynamics.
    for i in range(0, len(commands), 7):
        b.extend(bridge.step_commands(commands[i:i + 7]))
    assert project_trace(a) == project_trace(b), "Batch-dependent physics"
    checks["batch_partition_exact"] = True
    bridge.reset(42)
    held = bridge.step_commands([{**c, "down": True} for c in commands])
    assert project_trace(a) == project_trace(held), "Unexpected mouse-button dependence"
    checks["button_independent"] = True
    assert a[-1]["player_world_x"] > 100, "Hammer did not transfer force to body"
    checks["sweep_end_x"] = a[-1]["player_world_x"]
    checks["sweep_max_gain"] = max(s["player_world_y"] for s in a) - 21
    checks["sweep_hammer_hits"] = sum(s["hammer_collision"] for s in a)
    previous = start
    for i, s in enumerate(a):
        assert s["tick"] == previous["tick"] + 1
        assert s["frame_id"] == previous["frame_id"] + 1
        assert s["command_id_applied"] == i + 1
        assert abs(s["game_time"] - previous["game_time"] - 1 / metadata["frameRate"]) < 1e-10
        for prefix in ("player", "hammer"):
            for axis in ("x", "y"):
                assert abs(s[f"{prefix}_v{axis}"] -
                           (s[f"{prefix}_world_{axis}"] - previous[f"{prefix}_world_{axis}"])) < 1e-8
        assert abs(s["player_screen_x"] + s["camera_x"] - s["player_world_x"]) < 1e-8
        assert abs(s["player_screen_y"] + s["camera_y"] - s["player_world_y"]) < 1e-8
        previous = s
    checks["frame_ack_clock_velocity_camera"] = True
    checks["camera_x_range"] = max(s["camera_x"] for s in a) - min(s["camera_x"] for s in a)
    # Reads must not update finite differences or age any state.
    before = bridge.read_state()
    assert bridge.read_state() == before
    checks["read_is_pure"] = True
    checks["direct_mouse_property_reporter"] = bridge.evaluate(
        "(()=>{const mouse=vm.runtime.ioDevices.mouse;const old=mouse._scratchX;"
        "mouse._scratchX=77;const value=mouse.getScratchX();mouse._scratchX=old;return value;})()")
    assert checks["direct_mouse_property_reporter"] == 77
    bridge.reset(42)
    terrain = TerrainMap()
    # Interior/exterior points away from antialias boundaries, within active tiles.
    points = [[x, y] for x in range(-140, 141, 20) for y in range(-70, 91, 20)]
    actual = bridge.evaluate(f"window.research.terrain({json.dumps(points)})")
    predicted = [terrain.check_collision(x, y) for x, y in points]
    disagreements = [p for p, a, b in zip(points, actual, predicted) if a != b]
    checks["terrain_points"] = len(points)
    checks["terrain_disagreements"] = disagreements
    # A point hitbox covers a pixel footprint. Retain mismatches as evidence
    # rather than pretending a descriptor is an exact collision simulator.
    checks["terrain_agreement"] = 1 - len(disagreements) / len(points)
    assert checks["terrain_agreement"] > 0.95, "Terrain reference frame/scale mismatch"
    initial_metadata = bridge.evaluate("window.research.metadata()")
    for _ in range(30):
        reset_state = bridge.reset(42)
        assert reset_state["player_world_y"] == 21
        assert bridge.evaluate("window.research.metadata()") == initial_metadata, "Reset asset/clone leak"
    checks["thirty_resets_no_asset_or_clone_growth"] = initial_metadata
    # Isolated instrumentation: place the character over empty water. This is
    # a terminal-condition probe, not a gameplay trajectory or training reset.
    bridge.reset(42)
    bridge.evaluate(
        "(()=>{const vars=Object.values(vm.runtime.getTargetForStage().variables);"
        "for(const name of ['PLAYER X','HAMMER X']) vars.find(v=>v.name===name).value=-900;return true;})()")
    falling = bridge.step_commands([{"x": 0, "y": 0, "id": i + 1} for i in range(120)])
    assert falling[-1]["dead"] and falling[-1]["player_world_y"] < -180
    assert len(falling) < 120
    assert bridge.step_commands([{"x": 0, "y": 0, "id": 999}]) == []
    checks["death_stops_without_auto_restart"] = {
        "tick_count": len(falling), "last_y": falling[-1]["player_world_y"]}
    bridge.reset(42)
    checks["trajectory_sha256"] = hashlib.sha256(json.dumps(project_trace(a)).encode()).hexdigest()
    return {"checks": checks, "start": start, "commands": commands, "trace": a}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", choices=["auto", "embedded", "selenium"], default="auto")
    args = parser.parse_args()
    with BrowserBridge(driver=args.driver) as bridge:
        evidence = validate(bridge)
    output = ROOT / "artifacts" / ("validation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence["checks"], indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
