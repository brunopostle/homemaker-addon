#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest

import topologic
from topologic import Vertex, Edge, Wire, Face, Cell, CellComplex, Cluster, Topology
import topologist
from topologist import *

points = [[0,0,0], [10,0,0], [10,10,0], [0,10,0], [0,0,10], [10,0,10], [10,10,10], [0,10,10]]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [[0,1,2], [0,2,3], [1,2,6,5], [2,3,7,6], [0,4,7,3], [0,1,5,4], [4,5,6], [4,6,7], [0,2,6,4]]

faces = []
for face_by_id in faces_by_vertex_id:
    vertices_face = []
    for point_id in face_by_id:
        vertex = vertices[point_id]
        vertices_face.append(vertex)
    face = Face.ByVertices(vertices_face)
    faces.append(face)

cc = CellComplex.ByFaces2(faces, 0.0001)

class Tests(unittest.TestCase):
    def test_vertices(self):
        self.assertEqual(len(points), len(vertices))
        self.assertEqual(points[0][0], 0)
        self.assertEqual(points[1][0], 10)
        self.assertEqual(vertices[0].X(), 0)
        self.assertEqual(vertices[1].X(), 10)
        self.assertEqual(vertices[-1].Y(), 10)
    def test_faces(self):
        self.assertEqual(len(faces_by_vertex_id), len(faces))
        self.assertEqual(faces_by_vertex_id[0][2], 2)
        self.assertTrue(faces[0].IsHorizontal())
        self.assertFalse(faces[0].IsVertical())
        self.assertTrue(faces[2].IsVertical())
        self.assertTrue(faces[-1].IsVertical())
        faces_vertical = cc.FacesVertical()
        self.assertEqual(len(faces_vertical), 5)
        self.assertTrue(faces_vertical[0].IsVertical())
        self.assertTrue(faces_vertical[2].IsVertical())
        self.assertTrue(faces_vertical[4].IsVertical())
        faces_horizontal = cc.FacesHorizontal()
        self.assertEqual(len(faces_horizontal), 4)
    def test_cells(self):
        centroid = cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 5.0)
        self.assertEqual(centroid.Z(), 5.0)
        cells = getSubTopologies(cc, Cell)
        self.assertEqual(len(cells), 2)
        centroid_0 = cells[0].Centroid()
        centroid_1 = cells[1].Centroid()
        self.assertEqual(centroid_1.Z(), 5.0)
        volume_0 = cells[0].Volume()
        volume_1 = cells[1].Volume()
        self.assertAlmostEqual(volume_0, 500.0)
        self.assertAlmostEqual(volume_1, 500.0)

output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()
