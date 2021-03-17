#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import create_stl_list, vertex_id

points = [
    [0.0, 0.0, 0.0],
    [10.0, 0.0, 0.0],
    [10.0, 10.0, 0.0],
    [0.0, 10.0, 0.0],
    [5.0, 0.0, 3.0],
    [5.0, 10.0, 3.0],
]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [[0, 1, 2, 3], [0, 1, 4], [2, 3, 5], [1, 2, 5, 4], [0, 3, 5, 4]]

faces = []
for face_by_id in faces_by_vertex_id:
    vertices_face = []
    for point_id in face_by_id:
        vertex = vertices[point_id]
        vertices_face.append(vertex)
    face_by_vertices = Face.ByVertices(vertices_face)
    faces.append(face_by_vertices)

faces_ptr = create_stl_list(Face)
for face in faces:
    faces_ptr.push_back(face)
cc = CellComplex.ByFaces(faces_ptr, 0.0001)


class Tests(unittest.TestCase):
    """14 faces and three cells formed by a cube sliced on the diagonal"""

    def test_perimeter(self):
        roof_cluster = cc.Roof()
        roof_faces = create_stl_list(Face)
        roof_cluster.Faces(roof_faces)
        self.assertEqual(len(list(roof_faces)), 2)
        vertices = create_stl_list(Vertex)
        roof_cluster.Vertices(vertices)
        for vertex in vertices:
            i = vertex_id(roof_cluster, vertex)
            self.assertTrue(i > -1)
            self.assertTrue(i < 6)


if __name__ == "__main__":
    unittest.main()
