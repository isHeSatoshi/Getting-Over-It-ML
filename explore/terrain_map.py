"""ASCII map of real-renderer terrain around the end state of a saved path."""
import json, sys
from research.fast_bridge import FastBridge
path = json.load(open(sys.argv[1])); step = float(sys.argv[2]) if len(sys.argv) > 2 else 24
W, H = int(sys.argv[3]) if len(sys.argv) > 3 else 40, int(sys.argv[4]) if len(sys.argv) > 4 else 26
ndec = int(sys.argv[5]) if len(sys.argv) > 5 else len(path["actions"])
cmds, cid = [], 1
for ax, ay in path["actions"][:ndec]:
    for _ in range(path["hold"]): cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
with FastBridge(headless=True) as b:
    b.reset(0); s = None
    for i in range(0, len(cmds), 2400): tr = b.step_commands(cmds[i:i + 2400]); s = tr[-1]
    px, py, hx, hy = s["player_world_x"], s["player_world_y"], s["hammer_world_x"], s["hammer_world_y"]
    print(f"body ({px:.1f},{py:.1f}) hammer ({hx:.1f},{hy:.1f}) camera ({s['camera_x']:.1f},{s['camera_y']:.1f}) grid step {step}")
    xs = [px + (i - W // 2) * step for i in range(W)]; ys = [py + (H * 2 // 3 - j) * step for j in range(H)]  # more rows above
    pts = [[x, y] for y in ys for x in xs]
    hits = []
    for i in range(0, len(pts), 900): hits += b.evaluate(f"research.terrain({json.dumps(pts[i:i+900])})")
    for j, y in enumerate(ys):
        row = ""
        for i, x in enumerate(xs):
            c = "#" if hits[j * W + i] else "."
            if abs(x - px) < step / 2 and abs(y - py) < step / 2: c = "P"
            elif abs(x - hx) < step / 2 and abs(y - hy) < step / 2: c = "H"
            row += c
        print(f"{y:8.0f} {row}")
    print("x from", round(xs[0]), "to", round(xs[-1]))
