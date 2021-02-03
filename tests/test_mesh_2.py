#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Face, Cell, CellComplex, Topology

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list

points = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0],
          [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [10.0, 10.0, 10.0], [0.0, 10.0, 10.0]]

points.extend([[0.0, 0.0, 20.0], [10.0, 0.0, 20.0], [10.0, 10.0, 20.0], [0.0, 10.0, 20.0]])

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [[0, 1, 2], [0, 2, 3], [1, 2, 6, 5], [2, 3, 7, 6], [0, 4, 7, 3],
                      [0, 1, 5, 4], [4, 5, 6], [4, 6, 7], [0, 2, 6, 4]]

faces_by_vertex_id.extend([[4, 5, 9, 8], [5, 6, 10, 9], [6, 7, 11, 10], [7, 4, 8, 11],
                           [8, 9, 10, 11]])

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
    def test_faces_cc(self):

        faces_all = create_stl_list(Face)
        cc.Faces(faces_all)
        self.assertEqual(len(faces_all), 14)
        for face in faces_all:
            cells = create_stl_list(Cell)
            face.Cells(cells)
            self.assertGreater(len(cells), 0)
            self.assertLess(len(cells), 3)

        faces_vertical = create_stl_list(Face)
        cc.FacesVertical(faces_vertical)
        self.assertEqual(len(faces_vertical), 9)
        for face in faces_vertical:
            self.assertTrue(face.IsVertical())

        faces_horizontal = create_stl_list(Face)
        cc.FacesHorizontal(faces_horizontal)
        self.assertEqual(len(faces_horizontal), 5)
        for face in faces_horizontal:
            self.assertTrue(face.IsHorizontal())

    def test_cells(self):

        centroid = cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 5.0)
        self.assertEqual(centroid.Z(), 10.0)

        cells = create_stl_list(Cell)
        cc.Cells(cells)
        self.assertEqual(len(cells), 3)

        for cell in cells:
            centroid = cell.Centroid()
            volume = cell.Volume()

            faces_vertical = create_stl_list(Face)
            cell.FacesVertical(faces_vertical)

            faces_horizontal = create_stl_list(Face)
            cell.FacesHorizontal(faces_horizontal)

            cells_above = create_stl_list(Cell)
            cell.CellsAbove(cc, cells_above)
            if len(cells_above) == 1:
                self.assertAlmostEqual(volume, 500.0)
            elif len(cells_above) == 0:
                self.assertAlmostEqual(volume, 1000.0)

                faces_vertical = create_stl_list(Face)
                cell.FacesVertical(faces_vertical)

                for face in faces_vertical:
                    top_edges = create_stl_list(Edge)
                    bottom_edges = create_stl_list(Edge)

                    face.EdgesTop(top_edges)
                    face.EdgesBottom(bottom_edges)
                    self.assertEqual(len(top_edges), 1)
                    self.assertEqual(len(bottom_edges), 1)

                    self.assertFalse(face.IsFaceAbove())
                    self.assertTrue(face.IsFaceBelow())

            cells_below = create_stl_list(Cell)
            cell.CellsBelow(cc, cells_below)
            if len(cells_below) == 2:
                self.assertAlmostEqual(volume, 1000.0)
            elif len(cells_below) == 0:
                self.assertAlmostEqual(volume, 500.0)

    def test_faces(self):
        faces_vertical = create_stl_list(Face)
        cc.FacesVertical(faces_vertical)
        self.assertEqual(len(faces_vertical), 9)

        faces_vertical_internal = create_stl_list(Face)
        cc.FacesVerticalInternal(faces_vertical_internal)
        self.assertEqual(len(faces_vertical_internal), 1)

        faces_vertical_external = create_stl_list(Face)
        cc.FacesVerticalExternal(faces_vertical_external)
        self.assertEqual(len(faces_vertical_external), 8)

        faces_vertical_world = create_stl_list(Face)
        cc.FacesVerticalWorld(faces_vertical_world)
        self.assertEqual(len(faces_vertical_world), 8)

        faces_vertical_open = create_stl_list(Face)
        cc.FacesVerticalOpen(faces_vertical_open)
        self.assertEqual(len(faces_vertical_open), 0)

        faces_horizontal = create_stl_list(Face)
        cc.FacesHorizontal(faces_horizontal)
        self.assertEqual(len(faces_horizontal), 5)

        faces_horizontal_internal = create_stl_list(Face)
        cc.FacesHorizontalInternal(faces_horizontal_internal)
        self.assertEqual(len(faces_horizontal_internal), 2)

        faces_horizontal_external = create_stl_list(Face)
        cc.FacesHorizontalExternal(faces_horizontal_external)
        self.assertEqual(len(faces_horizontal_external), 3)

    def test_wires(self):
        walls_external = cc.WallsExternal()
        self.assertEqual(len(walls_external), 2)
        self.assertEqual(len(walls_external[0.0]), 1)
        self.assertEqual(len(walls_external[10.0]), 1)

        wire_lower = walls_external[0.0][10.0]
        vertices_lower = create_stl_list(Vertex)
        wire_lower.Vertices(vertices_lower)
        self.assertEqual(len(vertices_lower), 4)

        wire_upper = walls_external[10.0][10.0]
        vertices_upper = create_stl_list(Vertex)
        wire_upper.Vertices(vertices_upper)
        self.assertEqual(len(vertices_upper), 4)

    def test_elevations(self):
        elevations = cc.Elevations()
        self.assertEqual(len(elevations), 3)
        self.assertEqual(elevations[0.0], 0)
        self.assertEqual(elevations[10.0], 1)
        self.assertEqual(elevations[20.0], 2)

output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()