#!/usr/bin/python3

import os
import sys
import unittest
import numpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.geometry import (
    add_2d,
    angle_2d,
    distance_2d,
    normalise_2d,
    points_2line,
    line_intersection,
    transform,
)


class Tests(unittest.TestCase):
    """geometry functions"""

    def test_transform(self):
        identity_matrix = numpy.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        )
        scale_matrix = numpy.array(
            [[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 2]]
        )
        self.assertEqual(transform(identity_matrix, [2, 3, 4]), [2, 3, 4])
        self.assertEqual(transform(scale_matrix, [2, 3, 4]), [4, 6, 8])
        self.assertEqual(transform(identity_matrix, [2, 3]), [2, 3])
        self.assertEqual(transform(scale_matrix, [2, 3]), [4, 6])

    def test_add_2d(self):
        self.assertEqual(add_2d([2, 3], [5, -3]), [7.0, 0])
        self.assertEqual(add_2d([2.0, 3], [5, -3.0]), [7.0, 0])

    def test_angle_2d(self):
        self.assertEqual(angle_2d([2, 0], [5, 0]), 0)
        self.assertAlmostEqual(angle_2d([5, 0], [2, 0]), 3.14159265)
        self.assertAlmostEqual(angle_2d([2, -5], [2, 7]), 1.57079632)
        self.assertAlmostEqual(angle_2d([2, 7], [2, -5]), -1.57079632)

    def test_distance_2d(self):
        self.assertEqual(distance_2d([0, 0], [3, 4]), 5)
        self.assertEqual(distance_2d([1, -1], [-3, 2]), 5)

    def test_normalise_2d(self):
        self.assertEqual(normalise_2d([3, 4]), [0.6, 0.8])
        self.assertEqual(normalise_2d([-3, 4]), [-0.6, 0.8])
        self.assertEqual(normalise_2d([0, 0]), [1, 0])

    def test_points_2line(self):
        line = points_2line([1, 1], [2, 2])
        self.assertEqual(line["a"], 1)
        self.assertEqual(line["b"], 0)

        line2 = points_2line([3, 0], [3, 5])
        point = line_intersection(line, line2)
        self.assertAlmostEqual(point[0], 3)
        self.assertAlmostEqual(point[1], 3)

        line3 = points_2line([4, 0], [4, 5])
        point = line_intersection(line2, line3)
        self.assertEqual(point, None)


if __name__ == "__main__":
    unittest.main()
