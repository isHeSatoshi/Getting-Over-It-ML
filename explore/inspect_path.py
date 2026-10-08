import json, sys
from research.fast_bridge import FastBridge
path = json.load(open(sys.argv[1])); png = sys.argv[2]
cmds, cid = [], 1
for ax, ay in path["actions"]:
    for _ in range(path["hold"]):
        cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
with FastBridge(headless=True) as b:
    b.reset(0); tr = []
    for i in range(0, len(cmds), 2400): tr += b.step_commands(cmds[i:i + 2400])
    print("ticks", len(tr))
    for i in range(0, len(tr), max(100, len(tr) // 30)):
        s = tr[i]; print(f"t={i:5d} x={s['player_world_x']:8.1f} y={s['player_world_y']:8.1f} v=({s['player_vx']:6.1f},{s['player_vy']:6.1f}) body={int(s['body_collision'])} ham={int(s['hammer_collision'])}")
    s = tr[-1]; print("END", round(s["player_world_x"],1), round(s["player_world_y"],1), "dead", s["dead"])
    last = path["actions"][-1]
    hold = b.step_commands([{"x": last[0], "y": last[1], "id": cid+i} for i in range(180)])
    print("after 180-tick hold of last pointer:", round(hold[-1]["player_world_x"],1), round(hold[-1]["player_world_y"],1), "min y during hold", round(min(h["player_world_y"] for h in hold),1))
    print("max speed (units/tick):", round(max((s["player_vx"]**2+s["player_vy"]**2)**0.5 for s in tr),1))
    b.evaluate("research.render()")
    try:
        b.driver.save_screenshot(png); print("screenshot", png)
    except Exception as e: print("screenshot failed", e)
