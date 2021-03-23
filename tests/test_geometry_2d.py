#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.geometry_2d import (
    add_2d,
    angle_2d,
    distance_2d,
    is_between_2d,
    normalise_2d,
    points_2line,
    line_intersection,
)


class Tests(unittest.TestCase):
    """geometry_2d functions"""

    def test_add_2d(self):
        self.assertEqual(add_2d([2, 3], [5, -3]), [7.0, 0])
        self.assertEqual(add_2d([2.0, 3], [5, -3.0]), [7.0, 0])

    def test_angle_2d(self):
        self.assertEqual(angle_2d([2, 0], [5, 0]), 0)
        self.assertAlmostEqual(angle_2d([5, 0], [2, 0]), 3.14159265)
        self.assertAlmostEqual(angle_2d([2, -5], [2, 7]), 1.57079632)

    def test_distance_2d(self):
        self.assertEqual(distance_2d([0, 0], [3, 4]), 5)
        self.assertEqual(distance_2d([1, -1], [-3, 2]), 5)

    def test_is_between_2d(self):
        self.assertTrue(is_between_2d([1, 1], [0, 0], [2, 2]))
        self.assertFalse(is_between_2d([1, 1.01], [0, 0], [2, 2]))

    def test_normalise_2d(self):
        self.assertEqual(normalise_2d([3, 4]), [0.6, 0.8])

    def test_points_2line(self):
        line = points_2line([1, 1], [2, 2])
        self.assertEqual(line["a"], 1)
        self.assertEqual(line["b"], 0)

        line2 = points_2line([3, 0], [3, 5])
        point = line_intersection(line, line2)
        self.assertAlmostEqual(point[0], 3)
        self.assertAlmostEqual(point[1], 3)


if __name__ == "__main__":
    unittest.main()
