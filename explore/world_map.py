"""Whole-world terrain map from the game's own tile costumes (no physics), with a route overlay.

Writes explore/world/world_occ.npy (bool, UNIT world units per pixel) and PNGs.
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from research.terrain import TerrainMap

UNIT = 8                                    # world units per map pixel
out = Path("explore/world"); out.mkdir(parents=True, exist_ok=True)
tm = TerrainMap()
ext = {}
for (lx, ly), t in tm.tiles.items():
    left = lx * 464 - t["cx"] / 2; top = ly * 344 + t["cy"] / 2
    ext[(lx, ly)] = (left, top, left + t["width"] / 2, top - t["height"] / 2)
x0 = min(e[0] for e in ext.values()); x1 = max(e[2] for e in ext.values())
y0 = min(e[3] for e in ext.values()); y1 = max(e[1] for e in ext.values())
W = int(np.ceil((x1 - x0) / UNIT)); H = int(np.ceil((y1 - y0) / UNIT))
occ = np.zeros((H, W), bool)
f = 2 * UNIT                                 # tile pixels per map pixel (tile res = 2 px/unit)
for key, a in tm._alpha.items():
    left, top, _, _ = ext[key]
    h, w = a.shape; ph, pw = (-h) % f, (-w) % f
    a = np.pad(a, ((0, ph), (0, pw))).reshape((h + ph) // f, f, (w + pw) // f, f).max(axis=(1, 3))
    c0 = int(round((left - x0) / UNIT)); r0 = int(round((y1 - top) / UNIT))
    occ[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] |= a[:H - r0, :W - c0]
np.save(out / "world_occ.npy", occ)
json.dump({"unit": UNIT, "x0": x0, "y1": y1, "W": W, "H": H, "tiles": len(ext), "bounds": [x0, x1, y0, y1]}, open(out / "world_meta.json", "w"))
print(f"tiles={len(ext)} world x[{x0:.0f},{x1:.0f}] y[{y0:.0f},{y1:.0f}] map {W}x{H} px; solid frac {occ.mean():.3f}")
def to_px(x, y): return ((x - x0) / UNIT, (y1 - y) / UNIT)
route = None
if len(sys.argv) > 1:
    from research.fast_bridge import FastBridge
    path = json.load(open(sys.argv[1])); cmds, cid = [], 1
    for ax, ay in path["actions"]:
        for _ in range(path["hold"]): cmds.append({"x": ax, "y": ay, "id": cid}); cid += 1
    with FastBridge(headless=True) as b:
        b.reset(0); route = []
        for i in range(0, len(cmds), 2400):
            route += [(s["player_world_x"], s["player_world_y"]) for s in b.step_commands(cmds[i:i + 2400])]
    json.dump(route[::4], open(out / "route_xy.json", "w"))
img = Image.fromarray(np.where(occ, 40, 235).astype(np.uint8)).convert("RGB"); d = ImageDraw.Draw(img)
for yy in range(0, int(y1), 1000):
    px, py = to_px(x0, yy); d.line([(0, py), (W, py)], fill=(200, 200, 255), width=1); d.text((2, py - 10), f"Y{yy}", fill=(0, 0, 200))
for xx in range(int(np.ceil(x0 / 1000)) * 1000, int(x1), 1000):
    px, py = to_px(xx, y1); d.line([(px, 0), (px, H)], fill=(200, 200, 255), width=1); d.text((px + 2, 2), f"X{xx}", fill=(0, 0, 200))
if route:
    pts = [to_px(x, y) for x, y in route[::2]]; d.line(pts, fill=(220, 30, 30), width=2)
    ex, ey = to_px(*route[-1]); d.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], outline=(0, 160, 0), width=3)
img.save(out / "world_full.png"); print("saved", out / "world_full.png", img.size)
# crop around plateau
if route:
    cx_, cy_ = to_px(*route[-1]); r = 1100 / UNIT
    img.crop((int(cx_ - r), int(cy_ - r), int(cx_ + r), int(cy_ + r))).resize((880, 880), Image.NEAREST).save(out / "world_plateau.png")
