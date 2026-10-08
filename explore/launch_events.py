"""List high-speed events along a saved path and the pointer pattern leading into each."""
import json, math, sys
import numpy as np
from research.fast_bridge import FastBridge
path = json.load(open(sys.argv[1])); thr = float(sys.argv[2]) if len(sys.argv) > 2 else 30
acts = path["actions"]; H = path["hold"]
cmds, cid = [], 1
for ax, ay in acts:
    for _ in range(H): cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
with FastBridge(headless=True) as b:
    b.reset(0); tr = []
    for i in range(0, len(cmds), 2400): tr += b.step_commands(cmds[i:i + 2400])
sp = np.array([math.hypot(s["player_vx"], s["player_vy"]) for s in tr])
events, i = [], 0
while i < len(sp):
    if sp[i] > thr:
        j = i
        while j < len(sp) and sp[j] > thr * 0.5: j += 1
        k = i + int(np.argmax(sp[i:j])); events.append((k, sp[k], j - i)); i = j
    else: i += 1
print(f"{len(events)} events with speed > {thr} (ticks={len(tr)}, decisions={len(acts)})")
for k, v, dur in events[:14]:
    s = tr[k]; d = k // H
    pre = acts[max(0, d - 12):d + 1]
    ang = [round(math.degrees(math.atan2(y, x))) for x, y in pre]; rad = [round(math.hypot(x, y)) for x, y in pre]
    print(f"tick {k:5d} v={v:5.1f} dur={dur:3d} pos=({s['player_world_x']:.0f},{s['player_world_y']:.0f}) vel=({s['player_vx']:.0f},{s['player_vy']:.0f}) body={int(s['body_collision'])} ham={int(s['hammer_collision'])}")
    print("     pointer angle(deg):", ang); print("     pointer radius    :", rad)
