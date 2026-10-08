"""Regression test for explore/goexplore.py pick(): degenerate tiers must not produce NaN probabilities.

The E26 crash (`ValueError: Probabilities contain NaN`) happened when --local-radius kept only cells
whose progress was far below the (excluded) global max, so every tier weight underflowed to zero.
"""
import unittest

import numpy as np

from explore import goexplore as G


class _FakeRng:
    """random() forces a tier; choice() asserts the probability vector is usable."""

    def __init__(self, u):
        self.u = u

    def random(self):
        return self.u

    def choice(self, n, p=None):
        assert p is not None and np.all(np.isfinite(p)) and abs(p.sum() - 1.0) < 1e-9, p
        return 0


def _archive(cells):
    arch = G.Archive()
    for i, c in enumerate(cells):
        arch.cell_node[i] = i
        arch.info[i] = {"key": str(i), "snap": None, "tick": i, "x": 0.0, "y": c["y"],
                        "ry": c.get("ry", c["y"]), "chosen": 0, "retained": c["retained"]}
    return arch


class PickDegenerateTests(unittest.TestCase):
    def setUp(self):
        self._radius = G.LOCAL["radius"]

    def tearDown(self):
        G.LOCAL["radius"] = self._radius

    def test_all_zero_weights_fall_back_to_uniform(self):
        G.LOCAL["radius"] = 50.0
        arch = _archive([
            {"y": -1e6, "ry": 100.0, "retained": True},
            {"y": -1e6, "ry": 100.0, "retained": False},
            {"y": +1e6, "ry": 0.0, "retained": False},   # global progress max, outside the local radius
        ])
        node = G.pick(arch, _FakeRng(0.65))              # 0.65 -> novelty/high tier
        self.assertIn(node, list(arch.cell_node.values()))

    def test_normal_weights_still_normalised(self):
        arch = _archive([
            {"y": 100.0, "retained": True},
            {"y": 50.0, "retained": False},
        ])
        node = G.pick(arch, _FakeRng(0.1))               # 0.1 -> steep retained frontier tier
        self.assertIn(node, list(arch.cell_node.values()))


if __name__ == "__main__":
    unittest.main()
