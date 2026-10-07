"""Bounded component benchmark. Wall time is never measured with virtual Date."""
import argparse
from datetime import datetime, timezone
import json
import math
import statistics
import time

from research.browser_bridge import BrowserBridge, ROOT
from research.env import RealGettingOverItEnv
from research.provenance import fingerprint


def distribution(values):
    ordered = sorted(values)
    return {"median_ms": statistics.median(ordered) * 1000,
            "p95_ms": ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)] * 1000,
            "samples": len(ordered)}


def benchmark(bridge):
    report = {"runtime": bridge.evaluate("window.research.metadata()")}
    rpcs = []
    for _ in range(30):
        begin = time.perf_counter()
        assert bridge.evaluate("1") == 1
        rpcs.append(time.perf_counter() - begin)
    report["empty_rpc"] = distribution(rpcs)
    resets = []
    for _ in range(5):
        begin = time.perf_counter()
        bridge.reset(42)
        resets.append(time.perf_counter() - begin)
    report["reset"] = distribution(resets)
    if hasattr(bridge, "_rpc"):
        webdriver_times = []
        for _ in range(30):
            begin = time.perf_counter()
            assert BrowserBridge.evaluate(bridge, "1") == 1
            webdriver_times.append(time.perf_counter() - begin)
        report["webdriver_rpc_same_worker"] = distribution(webdriver_times)
    # Timings overlap: collision and draw are nested inside runtime._step.
    # WebGL draw timing measures submission/waits, not GPU-only execution.
    bridge.evaluate("""(()=>{
        const run=vm.runtime, renderer=vm.renderer;
        const step=run._step.bind(run), draw=renderer.draw.bind(renderer);
        const collision=renderer.isTouchingDrawables.bind(renderer);
        window.componentProfile={step_ms:0,draw_ms:0,collision_ms:0,draw_calls:0,collision_calls:0};
        run._step=function(){const t=performance.now();try{return step();}finally{componentProfile.step_ms+=performance.now()-t;}};
        renderer.draw=function(){const t=performance.now();try{return draw();}finally{componentProfile.draw_ms+=performance.now()-t;componentProfile.draw_calls++;}};
        renderer.isTouchingDrawables=function(...args){const t=performance.now();try{return collision(...args);}finally{componentProfile.collision_ms+=performance.now()-t;componentProfile.collision_calls++;}};
        return true;
    })()""")
    physics = []
    commands = [{"x": 90 * math.cos(-i * math.pi / 60), "y": 90 * math.sin(-i * math.pi / 60), "id": i + 1}
                for i in range(600)]
    for _ in range(3):
        bridge.reset(42)
        bridge.evaluate("Object.keys(componentProfile).forEach(k=>componentProfile[k]=0)")
        start = time.perf_counter()
        result = bridge.evaluate(f"""(()=>{{const t=performance.now();const trace=research.step({json.dumps(commands)});
            return {{js_ms:performance.now()-t,ticks:trace.length,profile:{{...componentProfile}}}};}})()""")
        result["wall_ms"] = (time.perf_counter() - start) * 1000
        physics.append(result)
    report["batched_engine"] = physics
    env = RealGettingOverItEnv(bridge=bridge, horizon=100, terrain=True)
    env.reset(seed=42)
    observation_times = []
    for _ in range(30):
        begin = time.perf_counter()
        env._obs(env.state)
        observation_times.append(time.perf_counter() - begin)
    report["python_observation_with_terrain"] = distribution(observation_times)
    env.terrain = None
    # Benchmark descriptor construction without changing the normal environment contract.
    old_space = env.observation_space
    from gymnasium import spaces
    import numpy as np
    env.observation_space = spaces.Box(-np.inf, np.inf, shape=(len(env.observation_feature_names),), dtype=np.float32)
    times = []
    for _ in range(30):
        begin = time.perf_counter()
        env._obs(env.state)
        times.append(time.perf_counter() - begin)
    report["python_observation_without_terrain"] = distribution(times)
    env.observation_space = old_space
    for terrain in (False, True):
        env = RealGettingOverItEnv(bridge=bridge, horizon=64, terrain=terrain)
        env.reset(seed=42)
        times = []
        begin_all = time.perf_counter()
        for _ in range(32):
            begin = time.perf_counter()
            env.step([0, -0.625])
            times.append(time.perf_counter() - begin)
        elapsed = time.perf_counter() - begin_all
        report["environment_terrain_" + str(terrain).lower()] = {
            **distribution(times), "decisions_per_second": len(times) / elapsed,
            "physics_ticks_per_second": len(times) * env.frame_skip / elapsed}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", choices=["embedded", "selenium"], default="selenium")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    output = ROOT / "artifacts" / ("benchmark_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(parents=True)
    begin = time.perf_counter()
    if args.fast:
        from research.fast_bridge import FastBridge
        worker = FastBridge(headless=False if args.headed else None)
    else:
        worker = BrowserBridge(driver=args.driver, headless=not args.headed)
    with worker as bridge:
        startup = time.perf_counter() - begin
        report = benchmark(bridge)
        report.update(startup_seconds=startup, driver="websocket" if args.fast else args.driver,
                      headed=args.headed, provenance=fingerprint())
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "provenance"}, indent=2))
    print("Evidence:", output)


if __name__ == "__main__":
    main()
