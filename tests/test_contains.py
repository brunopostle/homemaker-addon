#!/usr/bin/python3

import unittest

from topologic import Vertex, CellUtility

v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
cell = CellUtility.ByTwoCorners(v1, v2)

point1 = Vertex.ByCoordinates(0.41215598, -2.0419712, 0.31666728)
point2 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.31666728)
point3 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.1412814)


class Tests(unittest.TestCase):
    def test_contains(self):
        """0 == INSIDE, 1 = ON_BOUNDARY, 2 = OUTSIDE"""
        self.assertEqual(CellUtility.Contains(cell, point1), 2)
        self.assertEqual(CellUtility.Contains(cell, point1, 0.001), 2)
        self.assertEqual(CellUtility.Contains(cell, point2), 0)
        self.assertEqual(CellUtility.Contains(cell, point3), 1)


if __name__ == "__main__":
    unittest.main()
