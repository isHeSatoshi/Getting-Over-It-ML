import sys, time, json, math, resource, os
import numpy as np
from research.fast_bridge import FastBridge
secs = float(sys.argv[1]); chunk = int(sys.argv[2]); tag = sys.argv[3]
rng = np.random.default_rng(int(os.getpid()))
with FastBridge(headless=True) as b:
    b.reset(0); b.step_commands([{"x": 0.0, "y": 0.0, "id": i+1} for i in range(10)])
    h = b.snapshot()
    ticks = 0; calls = 0; t_end = time.perf_counter() + secs; t0 = time.perf_counter()
    while time.perf_counter() < t_end:
        b.restore(h)
        x = rng.uniform(-128, 128, 2)
        cm = [{"x": float(x[0]), "y": float(x[1]), "id": 11+i} for i in range(chunk)]
        tr = b.step_commands(cm); ticks += len(tr); calls += 1
    dt = time.perf_counter() - t0
    print(json.dumps({"tag": tag, "chunk": chunk, "ticks_per_s": round(ticks/dt), "calls_per_s": round(calls/dt, 1)}), flush=True)
