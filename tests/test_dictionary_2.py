#!/usr/bin/python3

import os
import sys
import unittest

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face

assert topologist.face


class Tests(unittest.TestCase):
    """Six faces formed by a cube"""

    def setUp(self):
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

        self.faces_ptr = []
        for face_by_id in faces_by_vertex_id:
            vertices_face = []
            for point_id in face_by_id:
                vertex = vertices[point_id]
                vertices_face.append(vertex)

            face = Face.ByVertices(vertices_face)
            face.Set("stylename", "orange")
            self.faces_ptr.append(face)

        self.cellcomplex = CellComplex.ByFaces(self.faces_ptr, 0.0001)
        self.cellcomplex.ApplyDictionary(self.faces_ptr)

    def test_faces(self):
        self.assertEqual(len(self.faces_ptr), 6)
        for face in self.faces_ptr:
            self.assertEqual(face.Get("stylename"), "orange")

    def test_faces_cellcomplex(self):
        faces_ptr = []
        self.cellcomplex.Faces(None, faces_ptr)
        self.assertEqual(len(faces_ptr), 6)
        for face in faces_ptr:
            if not face.IsVertical():
                continue
            self.assertEqual(face.Get("stylename"), "orange")


if __name__ == "__main__":
    unittest.main()
