#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist import ugraph
from topologist.helpers import vertex_string
from molior import Molior
import molior.ifc


class Tests(unittest.TestCase):
    def setUp(self):
        trace = ugraph.graph()
        vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
        vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
        vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
        vertex_3 = Vertex.ByCoordinates(1.0, 4.0, 3.15)
        coor_0 = vertex_string(vertex_0)
        coor_1 = vertex_string(vertex_1)
        coor_2 = vertex_string(vertex_2)
        coor_3 = vertex_string(vertex_3)

        # closed extrusion
        # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
        trace.add_edge({coor_1: [coor_2, [vertex_1, vertex_2, None, None, None]]})
        trace.add_edge({coor_0: [coor_1, [vertex_0, vertex_1, None, None, None]]})
        trace.add_edge({coor_2: [coor_3, [vertex_2, vertex_3, None, None, None]]})
        trace.add_edge({coor_3: [coor_0, [vertex_3, vertex_0, None, None, None]]})
        paths = trace.find_paths()

        ifc = molior.ifc.init("Our House", {3.15: 2})

        self.extrusion = Molior().GetIfc(
            ifc,
            "default",  # style
            "top-backward-up",  # condition
            2,  # level
            3.15,  # elevation
            0.05,  # height
            paths[0],  # chain
            None,  # circulation
        )

        # open extrusion
        trace = ugraph.graph()
        trace.add_edge({coor_1: [coor_2, [vertex_1, vertex_2, None, None, None]]})
        trace.add_edge({coor_0: [coor_1, [vertex_0, vertex_1, None, None, None]]})
        trace.add_edge({coor_2: [coor_3, [vertex_2, vertex_3, None, None, None]]})
        paths = trace.find_paths()

        self.extrusion2 = Molior().GetIfc(
            ifc,
            "default",  # style
            "top-backward-level",  # condition
            2,  # level
            3.15,  # elevation
            0.05,  # height
            paths[0],  # chain
            None,  # circulation
        )

    def test_sanity(self):
        self.assertEqual(len(self.extrusion), 1)
        self.assertEqual(self.extrusion[0].height, 0.0)
        self.assertEqual(self.extrusion[0].level, 2)
        self.assertEqual(self.extrusion[0].name, "eaves")
        self.assertEqual(self.extrusion[0].__dict__["class"], "Extrusion")


if __name__ == "__main__":
    unittest.main()
