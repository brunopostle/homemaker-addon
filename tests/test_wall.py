#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist import ugraph
from topologist.helpers import vertex_string
from molior import Molior


class Tests(unittest.TestCase):
    def setUp(self):
        trace = ugraph.graph()
        vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
        vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
        vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
        coor_0 = vertex_string(vertex_0)
        coor_1 = vertex_string(vertex_1)
        coor_2 = vertex_string(vertex_2)

        # a real wall would have a Face and one or two Cells
        # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
        trace.add_edge({coor_1: [coor_2, [vertex_1, vertex_2, None, None, None]]})
        trace.add_edge({coor_0: [coor_1, [vertex_0, vertex_1, None, None, None]]})
        paths = trace.find_paths()

        self.wall = Molior().GetMolior(
            "default",  # style
            "external",  # condition
            2,  # level
            3.15,  # elevation
            2.85,  # height
            paths[0],  # chain
            None,  # circulation
        )[0]

    def test_sanity(self):
        self.assertEqual(self.wall.length_segment(0), 4)
        self.assertEqual(self.wall.length_segment(1), 5)
        self.assertEqual(self.wall.height, 2.85)
        self.assertEqual(self.wall.level, 2)
        self.assertEqual(self.wall.name, "exterior")
        self.assertEqual(self.wall.__dict__["class"], "Wall")

    def test_query(self):
        self.assertEqual(self.wall.length_openings(0), 2.0)
        self.assertEqual(self.wall.length_openings(1), 4.1)
        self.assertEqual(self.wall.border(0)[0], 0.08)
        self.assertEqual(self.wall.border(0)[1], 0.08)
        self.assertEqual(self.wall.border(1)[0], 0.08)
        self.assertEqual(self.wall.border(1)[1], 0.08)

    def test_align_openings(self):
        self.assertEqual(self.wall.openings[0][0]["along"], 1.0)
        self.wall.align_openings(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 1.0)
        self.assertEqual(self.wall.openings[1][0]["along"], 0.25)
        self.wall.align_openings(1)
        self.assertEqual(self.wall.openings[1][0]["along"], 0.25)

    def test_fix_overlaps(self):
        self.assertEqual(len(self.wall.openings[0]), 1)
        self.wall.fix_overlaps(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 1.0)

        self.wall.openings[0].append(
            {"name": "toilet outside door", "along": 2.5, "size": 0}
        )
        self.wall.openings[0].append(
            {"name": "toilet outside door", "along": 0.5, "size": 0}
        )
        self.assertEqual(self.wall.openings[0][1]["along"], 2.5)
        self.assertEqual(self.wall.openings[0][2]["along"], 0.5)

        self.wall.fix_overlaps(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 1.0)
        self.assertEqual(self.wall.openings[0][1]["along"], 3.1)
        self.assertAlmostEqual(self.wall.openings[0][2]["along"], 4.2)

        self.wall.fix_overrun(0)
        self.assertAlmostEqual(self.wall.openings[0][0]["along"], -0.28)
        self.assertAlmostEqual(self.wall.openings[0][1]["along"], 1.82)
        self.assertAlmostEqual(self.wall.openings[0][2]["along"], 2.92)

        self.wall.fix_underrun(0)
        self.assertAlmostEqual(self.wall.openings[0][0]["along"], -0.28)

        self.wall.align_openings(0)
        self.assertEqual(self.wall.openings[0][1]["along"], 1.5)

    def test_fix_segment(self):
        self.wall.fix_segment(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 1.0)

        self.wall.fix_segment(1)
        self.assertEqual(self.wall.openings[1][0]["along"], 0.25)
        self.assertEqual(self.wall.openings[1][1]["along"], 2.75)

    def test_fix_heights(self):
        self.assertEqual(self.wall.openings[0][0]["size"], 3)
        self.wall.fix_heights(0)
        self.assertEqual(self.wall.openings[0][0]["size"], 3)


if __name__ == "__main__":
    unittest.main()
