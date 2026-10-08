"""Zoomed crop of the offline world map: python explore/crop.py xa xb ya yb out.png [scale] [route.json]"""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
occ = np.load('explore/world/world_occ.npy'); meta = json.load(open('explore/world/world_meta.json'))
u = meta['unit']; x0 = meta['x0']; y1 = meta['y1']
xa, xb, ya, yb = map(float, sys.argv[1:5]); name = sys.argv[5]; scale = int(sys.argv[6]) if len(sys.argv) > 6 else 4
c0 = int((xa-x0)/u); c1 = int((xb-x0)/u); r0 = int((y1-yb)/u); r1 = int((y1-ya)/u)
sub = occ[r0:r1, c0:c1]
im = Image.fromarray(np.where(sub > 0, 40, 235).astype('uint8')).convert('RGB').resize(((c1-c0)*scale, (r1-r0)*scale), Image.NEAREST)
d = ImageDraw.Draw(im)
step = 100 if (xb-xa) < 2000 else 500
for x in range(int(xa//step*step), int(xb)+1, step):
    if x < xa: continue
    px = (x-xa)/u*scale; d.line([(px, 0), (px, im.size[1])], fill=(150, 150, 255)); d.text((px+2, 2), f"X{x}", fill=(0, 0, 200))
for y in range(int(ya//step*step), int(yb)+1, step):
    if y < ya: continue
    py = (yb-y)/u*scale; d.line([(0, py), (im.size[0], py)], fill=(150, 150, 255)); d.text((2, py+2), f"Y{y}", fill=(0, 0, 200))
rp = sys.argv[7] if len(sys.argv) > 7 else 'explore/world/route_xy.json'
pts = json.load(open(rp))
d.line([((p[0]-xa)/u*scale, (yb-p[1])/u*scale) for p in pts], fill=(255, 0, 0), width=1)
im.save(name); print(name, im.size)
