import unittest

import numpy as np

from research.inference_probe import inputs_from_records, predict_batches, difference


class FixedInferenceTests(unittest.TestCase):
    def rows(self):
        return [{"observation": [i, -i], "action": [i / 10, -i / 10], "state": {"tick": i}}
                for i in range(4)]

    def test_next_observation_pairs_with_next_action(self):
        observations, actions = inputs_from_records(self.rows(), 2)
        self.assertEqual(observations.tolist(), [[0, 0], [1, -1], [2, -2]])
        np.testing.assert_array_equal(actions, np.asarray([[0.1, -0.1], [0.2, -0.2],
                                                           [0.3, -0.3]], dtype=np.float32))

    def test_autoreset_boundary_is_not_treated_as_continuous(self):
        rows = self.rows()
        rows[1]["state"] = None
        observations, _ = inputs_from_records(rows, 2)
        self.assertEqual(observations.tolist(), [[0, 0], [2, -2]])

    def test_bad_trace_shapes_and_nan_fail(self):
        rows = self.rows()
        rows[0]["observation"] = [float("nan"), 0]
        with self.assertRaises(ValueError):
            inputs_from_records(rows, 2)
        with self.assertRaises(ValueError):
            inputs_from_records(self.rows(), 3)

    def test_batch_partitions_preserve_order(self):
        class Policy:
            def predict(self, observations, deterministic=True):
                return observations / 10, None
        observations = np.asarray([[i, -i] for i in range(7)], dtype=np.float32)
        np.testing.assert_array_equal(predict_batches(Policy(), observations, 3),
                                      predict_batches(Policy(), observations, 1))

    def test_difference_reports_pointer_units_separately(self):
        result = difference(np.zeros((2, 2)), np.ones((2, 2)) * 0.01)
        self.assertAlmostEqual(result["max_pointer_difference_pixels"], 1.28)
        self.assertEqual(result["exactly_equal_elements_fraction"], 0)


if __name__ == "__main__":
    unittest.main()
