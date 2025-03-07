#!/usr/bin/python3

import unittest

from topologic_core import Vertex, CellUtility


class Tests(unittest.TestCase):
    def setUp(self):
        v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
        v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
        self.cell = CellUtility.ByTwoCorners(v1, v2)

        self.point1 = Vertex.ByCoordinates(0.41215598, -2.0419712, 0.31666728)
        self.point2 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.31666728)
        self.point3 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.1412814)

    def test_contains(self):
        """0 == INSIDE, 1 = ON_BOUNDARY, 2 = OUTSIDE"""
        self.assertEqual(CellUtility.Contains(self.cell, self.point1, 0.001), 2)
        self.assertEqual(CellUtility.Contains(self.cell, self.point1, 0.001), 2)
        self.assertEqual(CellUtility.Contains(self.cell, self.point2, 0.001), 0)
        self.assertEqual(CellUtility.Contains(self.cell, self.point3, 0.001), 1)


if __name__ == "__main__":
    unittest.main()
