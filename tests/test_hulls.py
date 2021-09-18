#!/usr/bin/python3

import os
import sys
import unittest

from topologic import (
    Vertex,
    Face,
    Cell,
    CellComplex,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import create_stl_list
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

        faces_ptr = create_stl_list(Face)
        for face in faces:
            faces_ptr.push_back(face)
        self.cc = CellComplex.ByFaces(faces_ptr, 0.0001)

    def test_faces_cc(self):

        faces_all = create_stl_list(Face)
        self.cc.Faces(faces_all)
        self.assertEqual(len(faces_all), 7)

        count = 0
        for face in faces_all:
            if face.IsUpward():
                count += 1
        self.assertEqual(count, 2)

        faces_vertical = create_stl_list(Face)
        self.cc.FacesVertical(faces_vertical)
        self.assertEqual(len(faces_vertical), 4)

        faces_horizontal = create_stl_list(Face)
        self.cc.FacesHorizontal(faces_horizontal)
        self.assertEqual(len(faces_horizontal), 1)

        faces_inclined = create_stl_list(Face)
        self.cc.FacesInclined(faces_inclined)
        self.assertEqual(len(faces_inclined), 2)

    def test_cells(self):

        centroid = self.cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 6.0)
        self.assertEqual(centroid.Z(), 7.0)  # average of vertex positions

        cells = create_stl_list(Cell)
        self.cc.Cells(cells)
        self.assertEqual(len(cells), 1)

    def test_traces(self):
        traces, hulls, normals, elevations = self.cc.GetTraces()

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
        traces, hulls, normals, elevations = self.cc.GetTraces()
        ifc = molior.ifc.init("My House", elevations)
        molior_object = Molior(
            file=ifc,
            circulation=None,
            elevations=elevations,
            traces=traces,
            hulls=hulls,
            normals=normals,
            cellcomplex=self.cc,
        )
        molior_object.execute()
        ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
