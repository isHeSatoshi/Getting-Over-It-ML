"""Greedy descent on phi from given world points; draw onto a crop.  python explore/phi_trace.py xa xb ya yb out.png scale x,y x,y ..."""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
phi = np.load('explore/world/phi.npy'); occ = np.load('explore/world/world_occ.npy'); meta = json.load(open('explore/world/world_meta.json'))
u, x0, y1 = meta['unit'], meta['x0'], meta['y1']; H, W = phi.shape
xa, xb, ya, yb = map(float, sys.argv[1:5]); name = sys.argv[5]; sc = int(sys.argv[6])
pts = [tuple(map(float, a.split(','))) for a in sys.argv[7:]]
c0 = int((xa-x0)/u); c1 = int((xb-x0)/u); r0 = int((y1-yb)/u); r1 = int((y1-ya)/u)
im = Image.fromarray(np.where(occ[r0:r1, c0:c1], 40, 235).astype('uint8')).convert('RGB').resize(((c1-c0)*sc, (r1-r0)*sc), Image.NEAREST); d = ImageDraw.Draw(im)
for x in range(int(xa//500*500), int(xb)+1, 500):
    if x >= xa: px = (x-xa)/u*sc; d.line([(px, 0), (px, im.size[1])], fill=(150, 150, 255)); d.text((px+2, 2), f"X{x}", fill=(0, 0, 200))
for y in range(int(ya//500*500), int(yb)+1, 500):
    if y >= ya: py = (yb-y)/u*sc; d.line([(0, py), (im.size[0], py)], fill=(150, 150, 255)); d.text((2, py+2), f"Y{y}", fill=(0, 0, 200))
cols = [(220, 0, 0), (0, 150, 0), (0, 0, 220), (200, 0, 200), (0, 170, 170)]
for i, (x, y) in enumerate(pts):
    r, c = int(round((y1-y)/u)), int(round((x-x0)/u)); path = [(r, c)]
    for _ in range(100000):
        r, c = path[-1]; best = None; bv = phi[r, c]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r+dr, c+dc
                if (dr or dc) and 0 <= rr < H and 0 <= cc < W and phi[rr, cc] < bv-1e-6: bv = phi[rr, cc]; best = (rr, cc)
        if best is None: break
        path.append(best)
    d.line([((c-c0)*sc, (r-r0)*sc) for r, c in path], fill=cols[i % 5], width=2)
    d.ellipse([(path[0][1]-c0)*sc-4, (path[0][0]-r0)*sc-4, (path[0][1]-c0)*sc+4, (path[0][0]-r0)*sc+4], outline=cols[i % 5])
    print((x, y), 'phi', float(phi[path[0]]), 'steps', len(path), 'end world', (x0+path[-1][1]*u, y1-path[-1][0]*u))
im.save(name)
