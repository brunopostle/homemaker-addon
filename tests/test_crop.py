#!/usr/bin/python3

import os
import sys
import unittest
import numpy

from topologic import (
    Vertex,
    Edge,
    Face,
    EdgeUtility,
    FaceUtility,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import (
    create_stl_list,
    x_product_3d,
    normalise_3d,
    magnitude_3d,
    scale_3d,
    subtract_3d,
    distance_3d,
)


class Tests(unittest.TestCase):
    """Testing non-rectangular walls"""

    def setUp(self):
        self.face = Face.ByVertices(
            [
                Vertex.ByCoordinates(1.0, 2.0, 0.0),
                Vertex.ByCoordinates(5.0, 2.0, 0.0),
                Vertex.ByCoordinates(5.0, 2.0, 4.0),
                Vertex.ByCoordinates(4.0, 2.0, 3.0),
                Vertex.ByCoordinates(3.0, 2.0, 4.0),
                Vertex.ByCoordinates(1.0, 2.0, 4.0),
            ]
        )

    def test_faces(self):
        self.assertEqual(FaceUtility.Area(self.face), 15.0)

        top = create_stl_list(Edge)
        self.face.EdgesTop(top)

        bottom = create_stl_list(Edge)
        self.face.EdgesBottom(bottom)

        crop = create_stl_list(Edge)
        self.face.EdgesCrop(crop)

        self.assertEqual(len(list(top)), 1)
        self.assertEqual(len(list(bottom)), 1)
        self.assertEqual(len(list(crop)), 2)

        self.assertAlmostEqual(EdgeUtility.Length(list(crop)[0]) ** 2, 2)
        self.assertAlmostEqual(EdgeUtility.Length(list(crop)[1]) ** 2, 2)

    def test_plane(self):
        crop = create_stl_list(Edge)
        self.face.EdgesCrop(crop)
        edge0 = list(crop)[0]
        start = edge0.StartVertex().Coordinates()
        end = edge0.EndVertex().Coordinates()
        vector = subtract_3d(end, start)
        perp_2d = [0 - vector[1], vector[0], 0.0]
        xprod = x_product_3d(vector, perp_2d)
        self.assertAlmostEqual(xprod[0], -0.707106781)
        self.assertAlmostEqual(xprod[1], 0.0)
        self.assertAlmostEqual(xprod[2], 0.707106781)


    def test_math(self):
        self.assertEqual(distance_3d([1.0, 0.0, 1.0], [1.0, 3.0, 5.0]), 5.0)
        self.assertEqual(scale_3d([1.0, 2.0, 3.0], 2.0), [2.0, 4.0, 6.0])
        self.assertEqual(scale_3d(-2.0, [1.0, 2.0, 3.0]), [-2.0, -4.0, -6.0])
        self.assertEqual(magnitude_3d([3.0, 4.0, 0.0]), 5.0)
        self.assertEqual(normalise_3d([0.0, 4.0, 0.0]), [0.0, 1.0, 0.0])
        self.assertEqual(normalise_3d([0.0, 0.0, 0.0]), [1.0, 0.0, 0.0])
        self.assertEqual(
            x_product_3d([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]), [0.0, 0.0, 1.0]
        )


if __name__ == "__main__":
    unittest.main()
