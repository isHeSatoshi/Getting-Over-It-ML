"""High-resolution (native 2 px/unit) occupancy crop from the level tile costumes. python explore/hires_crop.py xa xb ya yb out.png [scale] [route.json]"""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from research.terrain import TerrainMap
xa, xb, ya, yb = map(float, sys.argv[1:5]); out = sys.argv[5]; sc = int(sys.argv[6]) if len(sys.argv) > 6 else 1
tm = TerrainMap(); W = int((xb - xa) * 2); H = int((yb - ya) * 2); occ = np.zeros((H, W), bool)
for (lx, ly), t in tm.tiles.items():
    left = lx * 464 - t["cx"] / 2; top = ly * 344 + t["cy"] / 2; right = left + t["width"] / 2; bot = top - t["height"] / 2
    if right < xa or left > xb or bot > yb or top < ya: continue
    a = tm._alpha[(lx, ly)]
    c0 = int(round((left - xa) * 2)); r0 = int(round((yb - top) * 2))
    rs, cs = max(0, -r0), max(0, -c0); re, ce = min(a.shape[0], H - r0), min(a.shape[1], W - c0)
    if re > rs and ce > cs: occ[r0 + rs:r0 + re, c0 + cs:c0 + ce] |= a[rs:re, cs:ce] > 0
im = Image.fromarray(np.where(occ, 40, 235).astype(np.uint8)).convert("RGB")
if sc > 1: im = im.resize((W * sc, H * sc), Image.NEAREST)
d = ImageDraw.Draw(im); step = 50
for x in range(int(xa // step * step), int(xb) + 1, step):
    if x >= xa: px = (x - xa) * 2 * sc; d.line([(px, 0), (px, im.size[1])], fill=(170, 170, 255)); d.text((px + 2, 2), f"X{x}", fill=(0, 0, 200))
for y in range(int(ya // step * step), int(yb) + 1, step):
    if y >= ya: py = (yb - y) * 2 * sc; d.line([(0, py), (im.size[0], py)], fill=(170, 170, 255)); d.text((2, py + 2), f"Y{y}", fill=(0, 0, 200))
im.save(out); print(out, im.size, "solid frac", occ.mean())
