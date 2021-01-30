#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Face, Cell, CellComplex, Topology

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list

points = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0],
          [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [10.0, 10.0, 10.0], [0.0, 10.0, 10.0]]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [[0, 1, 2], [0, 2, 3], [1, 2, 6, 5], [2, 3, 7, 6], [0, 4, 7, 3],
                      [0, 1, 5, 4], [4, 5, 6], [4, 6, 7], [0, 2, 6, 4]]

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
    """Nine faces and two cells formed by a cube sliced on the diagonal"""
    def test_vertices(self):
        self.assertEqual(points[0][0], 0.0)
        self.assertEqual(points[1][0], 10.0)
    def test_vertices_cc(self):
        self.assertEqual(len(points), len(vertices))
        self.assertEqual(vertices[0].X(), 0.0)
        self.assertEqual(vertices[1].X(), 10.0)
        self.assertEqual(vertices[-1].Y(), 10.0)
    def test_faces(self):
        self.assertEqual(len(faces_by_vertex_id), len(faces))
        self.assertEqual(faces_by_vertex_id[0][2], 2.0)
        self.assertTrue(faces[0].IsHorizontal())
        self.assertFalse(faces[0].IsVertical())
        self.assertTrue(faces[2].IsVertical())
        self.assertTrue(faces[-1].IsVertical())
    def test_faces_cc(self):

        faces_all = create_stl_list(Face)
        cc.Faces(faces_all)
        self.assertEqual(len(faces_all), 9)
        for face in faces_all:
            cells = create_stl_list(Cell)
            face.Cells(cells)
            self.assertGreater(len(cells), 0)
            self.assertLess(len(cells), 3)

        faces_vertical = create_stl_list(Face)
        cc.FacesVertical(faces_vertical)
        self.assertEqual(len(faces_vertical), 5)
        for face in faces_vertical:
            self.assertTrue(face.IsVertical())

        faces_horizontal = create_stl_list(Face)
        cc.FacesHorizontal(faces_horizontal)
        self.assertEqual(len(faces_horizontal), 4)
        for face in faces_horizontal:
            self.assertTrue(face.IsHorizontal())

    def test_cells(self):

        centroid = cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 5.0)
        self.assertEqual(centroid.Z(), 5.0)

        cells = create_stl_list(Cell)
        cc.Cells(cells)
        self.assertEqual(len(cells), 2)

        for cell in cells:
            centroid = cell.Centroid()
            self.assertEqual(centroid.Z(), 5.0)
            volume = cell.Volume()
            self.assertAlmostEqual(volume, 500.0)
            self.assertEqual(cell.Elevation(), 0.0)
            self.assertEqual(cell.Height(), 10.0)

            faces_vertical = create_stl_list(Face)
            cell.FacesVertical(faces_vertical)
            self.assertEqual(len(faces_vertical), 3)

            cell_adjacent = False
            nowt_adjacent = False
            face_internal = False
            face_world = False
            for face in faces_vertical:
                cells_adjacent = create_stl_list(Cell)
                face.Cells(cells_adjacent)
                if len(cells_adjacent) == 2:
                    cell_adjacent = True
                elif len(cells_adjacent) == 1:
                    nowt_adjacent = True
                if face.IsInternal():
                    face_internal = True
                elif face.IsWorld():
                    face_world = True
            self.assertTrue(cell_adjacent)
            self.assertTrue(nowt_adjacent)
            self.assertTrue(face_internal)
            self.assertTrue(face_world)

            faces_horizontal = create_stl_list(Face)
            cell.FacesHorizontal(faces_horizontal)
            self.assertEqual(len(faces_horizontal), 2)

            faces_top = create_stl_list(Face)
            cell.FacesTop(faces_top)
            self.assertEqual(len(faces_top), 1)
            for face in faces_top:
                self.assertTrue(face.IsHorizontal())
                self.assertEqual(face.Elevation(), 10.0)
                self.assertEqual(face.Height(), 0.0)

            faces_bottom = create_stl_list(Face)
            cell.FacesBottom(faces_bottom)
            self.assertEqual(len(faces_bottom), 1)
            for face in faces_bottom:
                self.assertTrue(face.IsHorizontal())
                self.assertEqual(face.Elevation(), 0.0)
                self.assertEqual(face.Height(), 0.0)

output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()
