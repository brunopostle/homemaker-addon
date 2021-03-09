#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex, Edge, Face, Cell, CellUtility
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list

v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
cell = CellUtility.ByTwoCorners(v1, v2)

point1 = Vertex.ByCoordinates(0.4, -2.2, 0.3)
point2 = Vertex.ByCoordinates(0.5, -2.4, 0.3)
point3 = Vertex.ByCoordinates(0.5, -2.4, 0.7)

edge_a = Edge.ByStartVertexEndVertex(point1, point2)
edge_b = Edge.ByStartVertexEndVertex(point3, point2)
edge_c = Edge.ByStartVertexEndVertex(point1, point3)

class Tests(unittest.TestCase):
    def test_horizontal(self):
        self.assertTrue(edge_a.IsHorizontal())
        self.assertFalse(edge_b.IsHorizontal())
        self.assertFalse(edge_c.IsHorizontal())
    def test_vertical(self):
        self.assertFalse(edge_a.IsVertical())
        self.assertTrue(edge_b.IsVertical())
        self.assertFalse(edge_c.IsVertical())

    def test_below(self):
        edges = create_stl_list(Edge)
        cell.Edges(edges)
        faces_above = 0
        faces_below = 0
        cells_below = 0
        for edge in edges:
            if edge.IsHorizontal():
                if edge.FaceBelow():
                    faces_below += 1
                    self.assertEqual(edge.FaceBelow().__class__, Face)
                if edge.FaceAbove():
                    faces_above += 1
                    self.assertEqual(edge.FaceAbove().__class__, Face)
                if len(list(edge.CellsBelow())) == 1:
                    cells_below += 1
                    self.assertEqual(list(edge.CellsBelow())[0].__class__, Cell)
        self.assertEqual(faces_above, 4)
        self.assertEqual(faces_below, 4)
        self.assertEqual(cells_below, 4)

if __name__ == '__main__':
    unittest.main()
