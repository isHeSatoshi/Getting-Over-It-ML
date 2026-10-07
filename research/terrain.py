"""Terrain alpha descriptors, not a physics simulator.

The renderer remains the collision authority. Adjacent tile costumes overlap,
so the descriptor checks their union rather than selecting one nearest tile.
"""
import math
import numpy as np

from StaticCollisionMap import StaticCollisionMap
from research.browser_bridge import ROOT


class TerrainMap(StaticCollisionMap):
    def __init__(self):
        super().__init__(str(ROOT / "Getting Over It v1"))
        self._alpha = {key: np.asarray(tile["image"])[..., 3] > 0 for key, tile in self.tiles.items()}
        self._directions = np.asarray([
            (math.cos(i * 2 * math.pi / 16), math.sin(i * 2 * math.pi / 16)) for i in range(16)])

    def check_collision(self, wx, wy):
        ix, iy = math.floor(wx / 464), math.floor(wy / 344)
        for lx in (ix, ix + 1):
            for ly in (iy, iy + 1):
                tile = self.tiles.get((lx, ly))
                if tile is None:
                    continue
                x = math.floor((wx - lx * 464) * 2 + tile["cx"])
                y = math.floor(tile["cy"] - (wy - ly * 344) * 2)
                if 0 <= x < tile["width"] and 0 <= y < tile["height"]:
                    if tile["image"].getpixel((x, y))[3] > 0:
                        return True
        return False

    def _collisions(self, points):
        points = np.asarray(points, dtype=np.float64)
        flat = points.reshape(-1, 2)
        indices = np.floor(flat / (464, 344)).astype(np.int64)
        hit = np.zeros(len(flat), dtype=bool)
        lower, upper = indices.min(axis=0), indices.max(axis=0) + 1
        for lx in range(lower[0], upper[0] + 1):
            for ly in range(lower[1], upper[1] + 1):
                tile_key = (lx, ly)
                tile = self.tiles.get(tile_key)
                if tile is None:
                    continue
                selected = np.flatnonzero((indices[:, 0] >= lx - 1) & (indices[:, 0] <= lx)
                                          & (indices[:, 1] >= ly - 1) & (indices[:, 1] <= ly))
                local = flat[selected] - np.asarray(tile_key) * (464, 344)
                x = np.floor(local[:, 0] * 2 + tile["cx"]).astype(np.int64)
                y = np.floor(tile["cy"] - local[:, 1] * 2).astype(np.int64)
                valid = (x >= 0) & (x < tile["width"]) & (y >= 0) & (y < tile["height"])
                hit[selected[valid]] |= self._alpha[tile_key][y[valid], x[valid]]
        return hit.reshape(points.shape[:-1])

    def fast_observation(self, state):
        """Vectorized version of the identical 5-unit march and six bisections."""
        origins = np.repeat([[state["player_world_x"], state["player_world_y"]],
                             [state["hammer_world_x"], state["hammer_world_y"]]], 16, axis=0)
        directions = np.tile(self._directions, (2, 1))
        distances = np.arange(0, 151, 5, dtype=np.float64)
        hits = self._collisions(origins[:, None, :] + directions[:, None, :] * distances[None, :, None])
        active = hits.any(axis=1)
        first = hits.argmax(axis=1)
        hi = distances[first]
        lo = np.maximum(0, hi - 5)
        for _ in range(6):
            mid = (lo + hi) / 2
            collision = self._collisions(origins + directions * mid[:, None])
            hi = np.where(collision, mid, hi)
            lo = np.where(collision, lo, mid)
        points = origins + directions * hi[:, None]
        offsets = np.array([[3, 0], [-3, 0], [0, 3], [0, -3]])
        neighbors = self._collisions(points[:, None, :] + offsets).astype(np.int8)
        normals = np.stack((neighbors[:, 1] - neighbors[:, 0], neighbors[:, 3] - neighbors[:, 2]), axis=1)
        lengths = np.linalg.norm(normals, axis=1)
        normals = np.divide(normals, lengths[:, None], out=np.zeros_like(normals, dtype=float), where=lengths[:, None] > 0)
        normals[lengths == 0] = -directions[lengths == 0]
        rays = np.column_stack((np.where(active, hi, 150) / 150,
                                np.where(active[:, None], normals, 0), active.astype(float)))
        return rays.ravel().tolist()

    def observation(self, state):
        rays, _ = self.get_terrain_descriptor(
            state["player_world_x"], state["player_world_y"],
            state["hammer_world_x"], state["hammer_world_y"])
        return [value for dist, nx, ny, hit in rays
                for value in (dist / 150, nx, ny, hit)]
