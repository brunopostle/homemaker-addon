#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Face, CellComplex, Topology

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import create_stl_list

points = [
    [0.0, 0.0, 0.0],
    [10.0, 0.0, 0.0],
    [10.0, 10.0, 0.0],
    [0.0, 10.0, 0.0],
    [0.0, 0.0, 10.0],
    [10.0, 0.0, 10.0],
    [10.0, 10.0, 10.0],
    [0.0, 10.0, 10.0],
]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [
    [0, 1, 2, 3],
    [1, 2, 6, 5],
    [2, 3, 7, 6],
    [0, 4, 7, 3],
    [0, 1, 5, 4],
    [4, 5, 6, 7],
]

faces_ptr = create_stl_list(Face)
for face_by_id in faces_by_vertex_id:
    vertices_face = []
    for point_id in face_by_id:
        vertex = vertices[point_id]
        vertices_face.append(vertex)

    face = Face.ByVertices(vertices_face)
    face.Set("style", "orange")
    faces_ptr.push_back(face)

cellcomplex = CellComplex.ByFaces(faces_ptr, 0.0001)
cellcomplex.ApplyDictionary(faces_ptr)


class Tests(unittest.TestCase):
    """Six faces formed by a cube"""

    def test_faces(self):
        self.assertEqual(len(faces_ptr), 6)
        for face in faces_ptr:
            self.assertEqual(face.Get("style"), "orange")

    def test_faces_cellcomplex(self):
        faces_all = create_stl_list(Face)
        cellcomplex.Faces(faces_all)
        self.assertEqual(len(faces_all), 6)
        for face in faces_all:
            self.assertEqual(face.Get("style"), "orange")


output = Topology.Analyze(cellcomplex)
# print(output)

if __name__ == "__main__":
    unittest.main()
