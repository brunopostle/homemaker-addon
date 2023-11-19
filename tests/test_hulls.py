#!/usr/bin/python3

import os
import sys
import unittest

from topologic import (
    Vertex,
    Face,
    CellComplex,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
import molior.ifc


class Tests(unittest.TestCase):
    """A house shape"""

    def setUp(self):
        vertices = [
            Vertex.ByCoordinates(*point)
            for point in [
                [0.0, 0.0, 0.0],
                [10.0, 2.0, 0.0],
                [10.0, 12.0, 0.0],
                [0.0, 10.0, 0.0],
                [0.0, 0.0, 10.0],
                [10.0, 2.0, 10.0],
                [10.0, 12.0, 10.0],
                [0.0, 10.0, 10.0],
                [0.0, 5.0, 15.0],
                [10.0, 7.0, 15.0],
            ]
        ]

        faces_by_vertex_id = [
            [0, 1, 2, 3],
            [0, 1, 5, 4],
            [2, 3, 7, 6],
            [1, 2, 6, 9, 5],
            [0, 4, 8, 7, 3],
            [4, 5, 9, 8],
            [9, 8, 7, 6],
        ]

        faces = []
        for face_by_id in faces_by_vertex_id:
            vertices_face = []
            for point_id in face_by_id:
                vertex = vertices[point_id]
                vertices_face.append(vertex)
            face_by_vertices = Face.ByVertices(vertices_face)
            faces.append(face_by_vertices)

        faces_ptr = []
        for face in faces:
            faces_ptr.append(face)
        self.cc = CellComplex.ByFaces(faces_ptr, 0.0001)

    def test_faces_cc(self):
        all_faces_ptr = []
        self.cc.Faces(None, all_faces_ptr)
        self.assertEqual(len(all_faces_ptr), 7)

        count = 0
        for face in all_faces_ptr:
            if face.IsUpward():
                count += 1
        self.assertEqual(count, 2)

        vertical_faces_ptr = []
        self.cc.FacesVertical(vertical_faces_ptr)
        self.assertEqual(len(vertical_faces_ptr), 4)

        horizontal_faces_ptr = []
        self.cc.FacesHorizontal(horizontal_faces_ptr)
        self.assertEqual(len(horizontal_faces_ptr), 1)

        inclined_faces_ptr = []
        self.cc.FacesInclined(inclined_faces_ptr)
        self.assertEqual(len(inclined_faces_ptr), 2)

    def test_cells(self):
        centroid = self.cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 6.0)
        self.assertEqual(centroid.Z(), 7.0)  # average of vertex positions

        cells_ptr = []
        self.cc.Cells(None, cells_ptr)
        self.assertEqual(len(cells_ptr), 1)

    def test_traces(self):
        traces, normals, elevations = self.cc.GetTraces()
        hulls = self.cc.GetHulls()

        traces_external = traces["external"]
        self.assertEqual(len(traces_external), 1)
        self.assertEqual(len(traces_external[0.0]), 2)
        self.assertEqual(len(traces_external[0.0][10.0]), 1)
        self.assertEqual(len(traces_external[0.0][15.0]), 1)
        self.assertEqual(len(traces_external[0.0][10.0]["default"]), 2)
        self.assertEqual(len(traces_external[0.0][15.0]["default"]), 2)

        hulls_roof = hulls["roof"]
        self.assertEqual(len(hulls_roof), 1)
        self.assertEqual(len(hulls_roof["default"]), 1)

        self.assertEqual(len(hulls_roof["default"][0].nodes_all()), 6)
        self.assertEqual(len(hulls_roof["default"][0].faces_all()), 2)

        self.assertEqual(len(normals["top"].keys()), 4)
        self.assertEqual(len(normals["bottom"].keys()), 4)

    def test_ifc(self):
        traces, normals, elevations = self.cc.GetTraces()
        hulls = self.cc.GetHulls()
        ifc = molior.ifc.init(name="My Project")
        molior_object = Molior(
            file=ifc,
            circulation=None,
            traces=traces,
            hulls=hulls,
            name="My House",
            elevations=elevations,
            normals=normals,
            cellcomplex=self.cc,
        )
        molior_object.execute()
        ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
