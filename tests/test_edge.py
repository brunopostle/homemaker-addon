#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex, Edge, Face, Cell, CellUtility

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.edge


class Tests(unittest.TestCase):
    def setUp(self):
        v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
        v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
        self.cell = CellUtility.ByTwoCorners(v1, v2)

        point1 = Vertex.ByCoordinates(0.4, -2.2, 0.3)
        point2 = Vertex.ByCoordinates(0.5, -2.4, 0.3)
        point3 = Vertex.ByCoordinates(0.5, -2.4, 0.7)

        self.edge_a = Edge.ByStartVertexEndVertex(point1, point2)
        self.edge_b = Edge.ByStartVertexEndVertex(point3, point2)
        self.edge_c = Edge.ByStartVertexEndVertex(point1, point3)

    def test_horizontal(self):
        self.assertTrue(self.edge_a.IsHorizontal())
        self.assertFalse(self.edge_b.IsHorizontal())
        self.assertFalse(self.edge_c.IsHorizontal())

    def test_vertical(self):
        self.assertFalse(self.edge_a.IsVertical())
        self.assertTrue(self.edge_b.IsVertical())
        self.assertFalse(self.edge_c.IsVertical())

    def test_below(self):
        edges_ptr = []
        self.cell.Edges(None, edges_ptr)
        faces_above = 0
        faces_below = 0
        cells_below = 0
        for edge in edges_ptr:
            if edge.IsHorizontal():
                if edge.FaceBelow(self.cell):
                    faces_below += 1
                    self.assertEqual(type(edge.FaceBelow(self.cell)), Face)
                if edge.FaceAbove(self.cell):
                    faces_above += 1
                    self.assertEqual(type(edge.FaceAbove(self.cell)), Face)
                if len(list(edge.CellsBelow(self.cell))) == 1:
                    cells_below += 1
                    self.assertEqual(type(list(edge.CellsBelow(self.cell))[0]), Cell)
        self.assertEqual(faces_above, 4)
        self.assertEqual(faces_below, 4)
        self.assertEqual(cells_below, 4)


if __name__ == "__main__":
    unittest.main()
