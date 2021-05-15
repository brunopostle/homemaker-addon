#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
from molior import Molior
import molior.ifc


class Tests(unittest.TestCase):
    def setUp(self):
        trace = ugraph.graph()
        vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
        vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
        vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
        vertex_3 = Vertex.ByCoordinates(1.0, 4.0, 3.15)
        coor_0 = vertex_0.String()
        coor_1 = vertex_1.String()
        coor_2 = vertex_2.String()
        coor_3 = vertex_3.String()

        # closed repeat
        # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
        trace.add_edge({coor_1: [coor_2, [vertex_1, vertex_2, None, None, None]]})
        trace.add_edge({coor_0: [coor_1, [vertex_0, vertex_1, None, None, None]]})
        trace.add_edge({coor_2: [coor_3, [vertex_2, vertex_3, None, None, None]]})
        trace.add_edge({coor_3: [coor_0, [vertex_3, vertex_0, None, None, None]]})
        paths = trace.find_paths()

        ifc = molior.ifc.init("Our House", {3.15: 2})

        self.repeat = Molior().GetIfc(
            ifc,
            "fancy",  # style
            "top-backward-up",  # condition
            2,  # level
            3.15,  # elevation
            0.05,  # height
            paths[0],  # chain
            None,  # circulation
        )

        # open repeat
        trace = ugraph.graph()
        trace.add_edge({coor_1: [coor_2, [vertex_1, vertex_2, None, None, None]]})
        trace.add_edge({coor_0: [coor_1, [vertex_0, vertex_1, None, None, None]]})
        trace.add_edge({coor_2: [coor_3, [vertex_2, vertex_3, None, None, None]]})
        paths = trace.find_paths()

        self.repeat2 = Molior().GetIfc(
            ifc,
            "fancy",  # style
            "top-backward-level",  # condition
            2,  # level
            3.15,  # elevation
            0.05,  # height
            paths[0],  # chain
            None,  # circulation
        )

    def test_sanity(self):
        self.assertEqual(len(self.repeat), 2)
        self.assertEqual(self.repeat[0].height, 0.0)
        self.assertEqual(self.repeat[0].level, 2)
        self.assertEqual(self.repeat[0].name, "eaves")
        self.assertEqual(self.repeat[1].__dict__["class"], "Repeat")


if __name__ == "__main__":
    unittest.main()
