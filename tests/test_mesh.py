#!/usr/bin/python3

import os
import sys
import unittest
import cppyy

from topologic import Vertex, Face, Cell, CellComplex, Topology

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import topologist

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
    face = Face.ByVertices(vertices_face)
    faces.append(face)

cc = CellComplex.ByFaces2(faces, 0.0001)

class Tests(unittest.TestCase):
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
        faces_vertical = cc.FacesVertical()
        self.assertEqual(len(faces_vertical), 5)
        self.assertTrue(faces_vertical[0].IsVertical())
        self.assertTrue(faces_vertical[2].IsVertical())
        self.assertTrue(faces_vertical[4].IsVertical())
        faces_ptr2 = cppyy.gbl.std.list[Face.Ptr]()
        faces_horizontal = cc.FacesHorizontal()
        self.assertEqual(len(faces_horizontal), 4)

        faces_ptr3 = cppyy.gbl.std.list[Face.Ptr]()
        cc.Faces(faces_ptr3)
        self.assertEqual(len(faces_ptr3), 9)

        for face_cc in faces_ptr3:
            cells_ptr = cppyy.gbl.std.list[Cell.Ptr]()
            face_cc.Cells(cells_ptr)
            self.assertGreater(len(cells_ptr), 0)
            self.assertLess(len(cells_ptr), 3)

        faces_vertical = cc.FacesVertical()
        self.assertEqual(len(faces_vertical), 5)

        faces_ptr5 = cppyy.gbl.std.list[Face.Ptr]()
        faces_horizontal = cc.FacesHorizontal()
        self.assertEqual(len(faces_horizontal), 4)

    def test_cells(self):
        centroid = cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 5.0)
        self.assertEqual(centroid.Z(), 5.0)

        cells_ptr = cppyy.gbl.std.list[Cell.Ptr]()
        cc.Cells(cells_ptr)
        self.assertEqual(len(cells_ptr), 2)

        for cell in cells_ptr:
            centroid_0 = cell.Centroid()
            self.assertEqual(centroid_0.Z(), 5.0)
            volume_0 = cell.Volume()
            self.assertAlmostEqual(volume_0, 500.0)
            self.assertEqual(cell.Elevation(), 0.0)
            self.assertEqual(cell.Height(), 10.0)

            faces_ptr = cppyy.gbl.std.list[Face.Ptr]()
            faces_top = cell.FacesTop(faces_ptr)
            self.assertEqual(len(faces_top), 1)

            faces_ptr2 = cppyy.gbl.std.list[Face.Ptr]()
            faces_bottom = cell.FacesBottom(faces_ptr2)
            self.assertEqual(len(faces_bottom), 1)
            self.assertTrue(faces_top[0].IsHorizontal())
            self.assertEqual(faces_top[0].Elevation(), 10.0)
            self.assertEqual(faces_top[0].Height(), 0.0)

output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()
