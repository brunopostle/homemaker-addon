#!/usr/bin/python3

import unittest
import sys
import os

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
import topologist.vertex

assert topologist.vertex


class Tests(unittest.TestCase):
    def setUp(self):
        widgets_text = [
            ["Living", [0.0, 0.0, 1.0]],
        ]

        faces_text = [
            [
                [
                    [-1.0, -1.0, 0.0],
                    [1.0, -1.0, 0.0],
                    [1.0, 1.0, 0.0],
                    [-1.0, 1.0, 0.0],
                ],
                "default",
            ],
            [
                [
                    [-1.0, -1.0, 1.0],
                    [1.0, -1.0, 1.0],
                    [1.0, 1.0, 1.0],
                    [-1.0, 1.0, 1.0],
                ],
                "default",
            ],
            [
                [
                    [-1.0, -1.0, 0.0],
                    [-1.0, -1.0, 1.0],
                    [-1.0, 1.0, 1.0],
                    [-1.0, 1.0, 0.0],
                ],
                "default",
            ],
            [
                [
                    [1.0, -1.0, 0.0],
                    [1.0, -1.0, 1.0],
                    [1.0, 1.0, 1.0],
                    [1.0, 1.0, 0.0],
                ],
                "default",
            ],
            [
                [
                    [-1.0, 1.0, 0.0],
                    [-1.0, 1.0, 1.0],
                    [1.0, 1.0, 1.0],
                    [1.0, 1.0, 0.0],
                ],
                "blank",
            ],
            [
                [
                    [-1.0, -1.0, 0.0],
                    [-1.0, -1.0, 1.0],
                    [1.0, -1.0, 1.0],
                    [1.0, -1.0, 0.0],
                ],
                "blank",
            ],
        ]

        widgets = []
        for widget in widgets_text:
            vertex = Vertex.ByCoordinates(*widget[1])
            vertex.Set("usage", widget[0])
            widgets.append(vertex)

        faces_ptr = []
        for face in faces_text:
            face_ptr = Face.ByVertices([Vertex.ByCoordinates(*v) for v in face[0]])
            face_ptr.Set("stylename", face[1])
            faces_ptr.append(face_ptr)

        # Generate a Topologic CellComplex
        self.cc = CellComplex.ByFaces(faces_ptr, 0.0001)
        # Give every Cell and Face an index number
        self.cc.IndexTopology()
        # Copy styles from Faces to the CellComplex
        self.cc.ApplyDictionary(faces_ptr)
        # Assign Cell usages from widgets
        self.cc.AllocateCells(widgets)
        # Generate a circulation Graph
        self.circulation = self.cc.Adjacency()
        self.circulation.Circulation(self.cc)
        self.shortest_path_table = self.circulation.ShortestPathTable()
        self.circulation.Separation(self.shortest_path_table, self.cc)

    def test_molior(self):
        traces, normals, elevations = self.cc.GetTraces()
        hulls = self.cc.GetHulls()

        molior_object = Molior(
            circulation=self.circulation,
            traces=traces,
            hulls=hulls,
            normals=normals,
            cellcomplex=self.cc,
            name="My test building",
            elevations=elevations,
        )
        molior_object.execute()
        molior_object.file.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
