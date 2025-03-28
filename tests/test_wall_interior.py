#!/usr/bin/python3

import os
import sys
import unittest
from topologic_core import Vertex, Face, Graph

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph
import topologist.normals
from molior import Molior
import molior.ifc


class Tests(unittest.TestCase):
    def setUp(self):
        trace = topologist.ugraph.graph()
        normals = topologist.normals.Normals()
        vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
        vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
        vertex_2 = Vertex.ByCoordinates(5.0, 0.0, 6.00)
        vertex_3 = Vertex.ByCoordinates(1.0, 0.0, 6.00)
        coor_0 = vertex_0.CoorAsString()
        coor_1 = vertex_1.CoorAsString()

        dummy_cell = Vertex.ByCoordinates(0.0, 0.0, 0.0)

        face = Face.ByVertices([vertex_0, vertex_1, vertex_2, vertex_3])
        # a real wall would have a Face and one or two Cells
        trace.add_edge(
            {
                coor_0: [
                    coor_1,
                    {
                        "start_vertex": vertex_0,
                        "end_vertex": vertex_1,
                        "face": face,
                        "back_cell": None,
                        "front_cell": None,
                    },
                ]
            }
        )
        paths = trace.find_paths()

        ifc = molior.ifc.init(name="Our Project")

        molior_object = Molior(
            file=ifc,
            circulation=Graph,
            normals=normals.normals,
            cellcomplex=dummy_cell,
            name="My House",
            elevations={3.15: 2},
        )
        molior_object.init_building()
        self.wall = molior_object.build_trace(
            stylename="default",
            condition="internal",
            elevation=3.15,
            height=2.85,
            chain=paths[0],
        )[0]

        self.wall.populate_interior_openings(0, "living", "living", 0)
        self.wall.fix_heights(0)
        self.wall.fix_segment(0)

    def test_sanity(self):
        self.assertEqual(self.wall.length_segment(0), 4)
        self.assertEqual(self.wall.height, 2.85)
        self.assertEqual(self.wall.level, 2)
        self.assertEqual(self.wall.name, "interior")
        self.assertEqual(self.wall.__dict__["class"], "Wall")

    def test_query(self):
        self.assertEqual(self.wall.length_openings(0), 1.0)
        self.assertEqual(self.wall.border(0)[0], 0.08)
        self.assertEqual(self.wall.border(0)[1], 0.08)

    def test_align_openings(self):
        self.assertEqual(self.wall.openings[0][0]["along"], 0.5)
        self.wall.align_openings(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 0.5)

    def test_fix_overlaps(self):
        self.assertEqual(len(self.wall.openings[0]), 1)
        self.wall.fix_overlaps(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 0.5)

        self.wall.openings[0].append(
            {"family": "toilet outside door", "along": 2.5, "size": 0}
        )
        self.wall.openings[0].append(
            {"family": "toilet outside door", "along": 0.5, "size": 0}
        )
        self.assertEqual(self.wall.openings[0][1]["along"], 2.5)
        self.assertEqual(self.wall.openings[0][2]["along"], 0.5)

        self.wall.fix_overlaps(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 0.5)
        self.assertEqual(self.wall.openings[0][1]["along"], 2.5)
        self.assertAlmostEqual(self.wall.openings[0][2]["along"], 3.6)

        self.wall.fix_overrun(0)
        self.assertAlmostEqual(self.wall.openings[0][0]["along"], -0.18)
        self.assertAlmostEqual(self.wall.openings[0][1]["along"], 1.82)
        self.assertAlmostEqual(self.wall.openings[0][2]["along"], 2.92)

        self.wall.fix_underrun(0)
        self.assertAlmostEqual(self.wall.openings[0][0]["along"], 0.18)

        self.wall.align_openings(0)
        self.assertAlmostEqual(self.wall.openings[0][1]["along"], 1.82)

    def test_fix_segment(self):
        self.wall.fix_segment(0)
        self.assertEqual(self.wall.openings[0][0]["along"], 0.5)

    def test_fix_heights(self):
        self.assertEqual(self.wall.openings[0][0]["size"], 0)
        self.wall.fix_heights(0)
        self.assertEqual(self.wall.openings[0][0]["size"], 0)


if __name__ == "__main__":
    unittest.main()
