#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Wall, Molior
from molior.geometry import distance_2d


class Tests(unittest.TestCase):
    """Wall subclasses Molior"""

    def test_wall(self):
        wall = Wall()

        self.assertEqual(wall.height, 0.0)
        wall.height = 3.0
        self.assertEqual(wall.height, 3.0)

        self.assertEqual(wall.outer, 0.25)
        wall.outer = 0.3
        self.assertEqual(wall.outer, 0.3)

    def test_wall2(self):
        wall2 = Wall({"height": 2.7, "outer": 0.4})
        self.assertEqual(wall2.height, 2.7)
        self.assertEqual(wall2.outer, 0.4)

    def test_wall3(self):
        wall3 = Wall(
            {
                "closed": False,
                "path": [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]],
                "extension": 0.25,
                "condition": "external",
                "normals": {"top": {}, "bottom": {}},
                "normal_set": "top",
            }
        )
        wall3.init_openings()
        self.assertEqual(len(wall3.path), 3)
        self.assertEqual(len(wall3.openings), 2)
        self.assertEqual(wall3.segments(), 2)
        self.assertEqual(wall3.length_segment(0), 5)
        self.assertEqual(wall3.length_segment(1), 50 ** 0.5)
        self.assertEqual(wall3.length_segment(2), 125 ** 0.5)
        self.assertEqual(wall3.angle_segment(0), 0.0)
        self.assertEqual(wall3.angle_segment(1), 45.0)
        self.assertAlmostEqual(wall3.angle_segment(2), 206.5650512)
        self.assertEqual(wall3.direction_segment(0), [1, 0])
        self.assertEqual(wall3.normal_segment(0), [0, -1])
        self.assertEqual(wall3.corner_coor(0), [0, 0])
        self.assertEqual(wall3.corner_coor(1), [5, 0])
        self.assertEqual(wall3.corner_coor(2), [10, 5])
        self.assertEqual(wall3.corner_coor(3), [0, 0])
        self.assertEqual(wall3.corner_coor(4), [5, 0])
        self.assertEqual(wall3.corner_coor(5), [10, 5])
        self.assertEqual(wall3.corner_coor(6), [0, 0])
        self.assertEqual(wall3.corner_coor(-1), [10, 5])
        self.assertEqual(wall3.corner_offset(0, 0.5), [0, -0.5])
        self.assertEqual(wall3.corner_offset(0, -5), [0, 5])
        self.assertEqual(wall3.corner_offset(1, 0.0), [5, 0])
        self.assertAlmostEqual(wall3.corner_offset(1, 5.0)[0], 7.0710678)
        self.assertAlmostEqual(wall3.corner_offset(1, 5.0)[1], -5.0)
        self.assertEqual(wall3.corner_offset(2, 0.0), [10, 5])
        self.assertEqual(wall3.corner_in(0), [0, 0.08])
        self.assertEqual(wall3.corner_out(0), [0, -0.25])
        self.assertEqual(wall3.extension_start(), [-0.25, 0.0])
        self.assertAlmostEqual(distance_2d(wall3.extension_end(), [0, 0]), 0.25)

    def test_wall4(self):
        wall4 = Wall(
            {
                "closed": True,
                "path": [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]],
                "normals": {"top": {}, "bottom": {}},
                "condition": "internal",
                "normal_set": "top",
            }
        )
        wall4.init_openings()
        self.assertEqual(len(wall4.path), 3)
        self.assertEqual(len(wall4.openings), 3)
        self.assertEqual(wall4.path[2], [10.0, 5.0])
        self.assertEqual(wall4.segments(), 3)

        wall4.populate_exterior_openings(2, "kitchen", 0)
        self.assertEqual(
            wall4.openings[2][0],
            {"name": "kitchen outside window", "along": 0.5, "size": 0},
        )

        self.assertEqual(wall4.__dict__["guid"], "my building")

    def test_molior(self):
        molior = Molior()
        self.assertEqual(molior.share_dir, "share")
        self.assertEqual(
            Molior.style.get("default")["traces"]["exterior"]["condition"], "external"
        )


if __name__ == "__main__":
    unittest.main()
