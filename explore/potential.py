"""Geometry potential from the offline world map.

phi(p) = cheapest cost to reach the goal region: crossing free space costs distance (upward x UP_MULT,
downward x DOWN_MULT), moving over solid pixels costs SOLID_COST per unit. Saves explore/world/phi.npy
(float32, same grid as world_occ.npy) and prints/plots the cheapest route from spawn.
"""
import json, os, sys
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

UP, DOWN = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0, float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
SOLID_UP, SOLID_H, SOLID_DOWN = 0.5, 0.3, 0.1                         # moving along/over solid surface (per unit)
occ = np.load('explore/world/world_occ.npy'); meta = json.load(open('explore/world/world_meta.json'))
u, x0, y1 = meta['unit'], meta['x0'], meta['y1']; H, W = occ.shape
idx = np.arange(H * W).reshape(H, W)
K_EDT = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0                    # free-space cost density 1 + edt/K_EDT (superlinear gap cost)
edt = distance_transform_edt(~occ) * u
K_IN = float(sys.argv[4]) if len(sys.argv) > 4 else 16.0                      # solid cost density 1 + depth/K_IN: hug surfaces, don't tunnel through mass
edt_in = distance_transform_edt(occ) * u
COVER = float(os.environ.get('PHI_COVER', '1'))                              # free pixels with solid within 200 units above cost x COVER (no hanging under ceilings)
covered = np.zeros_like(occ)
for k in range(1, 26): covered[k:] |= occ[:-k]
covered &= ~occ
cover_mult = 1.0 + (COVER - 1.0) * covered
rows, cols, w = [], [], []
def add(dr, dc):
    r0, r1 = max(0, -dr), H - max(0, dr); c0, c1 = max(0, -dc), W - max(0, dc)
    a = idx[r0:r1, c0:c1]; b = idx[r0 + dr:r1 + dr, c0 + dc:c1 + dc]       # edge a -> b
    dist = u * np.hypot(dr, dc)
    up = (dr < 0)                                                          # row decreasing = world y up
    dens = (1.0 + edt[r0 + dr:r1 + dr, c0 + dc:c1 + dc] / K_EDT) * cover_mult[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
    smult = SOLID_UP if dr < 0 else (SOLID_DOWN if dr > 0 else SOLID_H)
    sdens = 1.0 + edt_in[r0 + dr:r1 + dr, c0 + dc:c1 + dc] / K_IN
    mult = np.where(occ[r0 + dr:r1 + dr, c0 + dc:c1 + dc] & occ[r0:r1, c0:c1], smult * sdens,
                    (UP if dr < 0 else (DOWN if dr > 0 else 1.0)) * dens)
    rows.append(a.ravel()); cols.append(b.ravel()); w.append((dist * mult).ravel().astype(np.float32))
for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
    add(dr, dc)
rows = np.concatenate(rows); cols = np.concatenate(cols); w = np.concatenate(w)
# goal: solid pixels with world y >= 14500 (reverse graph: run from the goal on transposed edges)
G = coo_matrix((w, (cols, rows)), shape=(H * W, H * W)).tocsr()             # transposed: dijkstra from goal gives cost-to-goal
gy = np.arange(H) * -u + y1
import os
GB = os.environ.get('PHI_GOAL_BOX')                                          # 'xa,xb,ya,yb': alternate goal region (solid pixels inside)
TAG = os.environ.get('PHI_TAG', '')
if GB:
    xa, xb, ya, yb = map(float, GB.split(','))
    gx = np.arange(W) * u + x0
    m = occ & (gy[:, None] >= ya) & (gy[:, None] <= yb) & (gx[None, :] >= xa) & (gx[None, :] <= xb)
    goal = [int(i) for i in idx[m]]
else:
    goal_rows = np.where((gy >= 14500))[0]
    goal = [int(i) for i in idx[goal_rows][occ[goal_rows]]]
print('goal px', len(goal))
d = dijkstra(G, directed=True, indices=goal, min_only=True)
phi = d.reshape(H, W).astype(np.float32)
phi[~np.isfinite(phi)] = np.nanmax(phi[np.isfinite(phi)]); np.save(f'explore/world/phi{TAG}.npy', phi)
np.save(f'explore/world/phi_x4{TAG}.npy', phi[::4, ::4].copy())                  # coarse grid (32 units) for the page-side gate
def px(x, y): return int(round((y1 - y) / u)), int(round((x - x0) / u))
r, c = px(0, 21); print('phi(spawn)', phi[r, c])
# cheapest route from spawn by greedy descent on phi
path = [(r, c)]
for _ in range(200000):
    r, c = path[-1]; best = None; bv = phi[r, c]
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = r + dr, c + dc
            if (dr or dc) and 0 <= rr < H and 0 <= cc < W and phi[rr, cc] < bv - 1e-6: bv = phi[rr, cc]; best = (rr, cc)
    if best is None: break
    path.append(best)
print('route px', len(path), 'end', path[-1])
json.dump([[x0 + c * u, y1 - r * u] for r, c in path], open('explore/world/phi_route.json', 'w'))
img = Image.fromarray(np.where(occ, 40, 235).astype(np.uint8)).convert('RGB'); dr_ = ImageDraw.Draw(img)
dr_.line([(c, r) for r, c in path], fill=(0, 160, 0), width=2)
img.save('explore/world/phi_route.png')
for name, (x, y) in {'tower_tip': (1500, 5054), 'plank_left': (2850, 3950), 'pillar': (3500, 3750), 'blob_1900_4400': (2000, 4400)}.items():
    r, c = px(x, y); print(name, (x, y), 'phi', float(phi[r, c]))
