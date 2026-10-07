"""Exact feature parity on static asset points; never a substitute for physics."""
import random
import unittest
import numpy as np
from research.terrain import TerrainMap


class TerrainParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terrain = TerrainMap()

    def test_points_match_scalar_at_boundaries(self):
        points = [(x, y) for x in (-464, -232, -1e-12, 0, 1e-12, 232, 464, 696)
                  for y in (-344, -172, -1e-12, 0, 1e-12, 172, 344)]
        actual = self.terrain._collisions(points)
        expected = [self.terrain.check_collision(*p) for p in points]
        self.assertTrue(np.array_equal(actual, expected))

    def test_descriptors_match_across_world_regions(self):
        rng = random.Random(0)
        positions = [(0, 21), (232, 344), (464, 172), (1000, 12000), (4000, 15000)]
        positions += [(rng.uniform(-500, 5000), rng.uniform(-100, 16000)) for _ in range(30)]
        for px, py in positions:
            state = {"player_world_x": px, "player_world_y": py,
                     "hammer_world_x": px + 70, "hammer_world_y": py + 30}
            self.assertTrue(np.allclose(self.terrain.observation(state), self.terrain.fast_observation(state),
                                        rtol=0, atol=1e-12), (px, py))


if __name__ == "__main__":
    unittest.main()
