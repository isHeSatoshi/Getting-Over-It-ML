"""Run one saved goal-SAC checkpoint in a visible browser with real-time pacing.

Local visualization only: no HF writes, no training, no budget. The policy is
the same learned-only evaluation path used by research.goal_evaluation, but
with a headed browser window and console telemetry.
"""
import argparse
import json
import math
from pathlib import Path
import time

import torch
from stable_baselines3 import SAC

from research.browser_bridge import BrowserBridge
from research.case_clock import PhysicalCaseClock
from research.env import RealGettingOverItEnv
from research.goal_archive import WaypointSupervisor
from research.goal_env import GoalEnv
from research.goal_study import CASES
from research.goal_train import SpacesOnly
from research.study_metrics import enable_platform_support


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True, help="Directory containing model.zip")
    parser.add_argument("--supervisor", type=Path, required=True, help="supervisor.json with stable waypoints")
    parser.add_argument("--cases", nargs="+", default=["nominal"],
                        help="Case names from the pilot evaluation set")
    parser.add_argument("--ticks", type=int, default=3600)
    parser.add_argument("--fps", type=float, default=30.0, help="Pacing target; 0 runs as fast as possible")
    parser.add_argument("--print-every", type=int, default=30)
    args = parser.parse_args()
    for path in (args.checkpoint, args.supervisor):
        if not path.is_absolute():
            parser.error("Use absolute checkpoint/supervisor paths")
    if not 1 <= args.ticks <= 3600 or args.fps < 0:
        parser.error("Invalid tick/pacing bounds")
    cases = {case.name: case for case in CASES}
    unknown = [name for name in args.cases if name not in cases]
    if unknown:
        parser.error(f"Unknown cases {unknown}; available: {sorted(cases)}")
    targets = json.loads(args.supervisor.read_text())["waypoints"]

    torch.set_num_threads(1)
    model = SAC.load(args.checkpoint / "model.zip", env=SpacesOnly(), device="cpu")
    print(f"Loaded checkpoint {args.checkpoint} | waypoints {len(targets)}", flush=True)

    with BrowserBridge(driver="selenium", headless=False) as bridge:
        for name in args.cases:
            case = cases[name]
            raw = RealGettingOverItEnv(bridge=bridge, action_mode="absolute", terrain=True,
                                       frame_skip=1, horizon=args.ticks)
            enable_platform_support(raw)
            env = GoalEnv(raw)
            supervisor = WaypointSupervisor(targets)
            env.reset(seed=case.reset_seed)
            observation = env.set_goal(supervisor.goal())
            clock = PhysicalCaseClock(case)
            started = time.time()
            sustained, achieved, first_ledge = 0, False, False
            print(f"\n=== case {name} (reset seed {case.reset_seed}) ===", flush=True)
            state, info = raw.state, None
            for tick in range(args.ticks):
                issued = model.predict(observation, deterministic=True)[0].astype("float32")
                applied = clock.apply(issued[None, :], tick)[0]
                observation, _, terminal, truncated, info = env.step_recorded(
                    issued, applied, category="evaluation", eligible=False)
                state = raw.state
                speed = math.hypot(state["player_vx"], state["player_vy"])
                first_ledge = bool(info["milestone_success"]["first_ledge_v1"])
                qualified = state["player_world_y"] >= 180 and speed <= 2 and not info["dead"]
                sustained = sustained + 1 if qualified else 0
                achieved |= sustained >= 90
                goal = supervisor.observe(state, first_ledge)
                observation = env.set_goal(goal)
                if tick % args.print_every == 0 or terminal or truncated:
                    print(f"t={tick+1:4d}  game_tick={state['tick']:5d}  "
                          f"pos=({state['player_world_x']:7.1f},{state['player_world_y']:7.1f})  "
                          f"speed={speed:5.2f}  waypoint={supervisor.target}/{len(targets)}  "
                          f"hold={supervisor.hold:2d}  ledge={'YES' if first_ledge else '-'}  "
                          f"y180hold={'YES' if achieved else '-'}", flush=True)
                if args.fps > 0:
                    delay = (tick + 1) / args.fps - (time.time() - started)
                    if delay > 0:
                        time.sleep(delay)
                if terminal or truncated:
                    break
            elapsed = time.time() - started
            print(f"case {name} done: ticks={tick+1}  final=({state['player_world_x']:.1f},{state['player_world_y']:.1f})  "
                  f"retained={state['player_world_y'] - 21:.1f}  first_ledge={first_ledge}  y180hold90={achieved}  "
                  f"dead={info['dead']}  summit={info['success']}  elapsed={elapsed:.0f}s", flush=True)
            env.close()
            time.sleep(1.0)
    print("\nViewer finished.")


if __name__ == "__main__":
    main()
