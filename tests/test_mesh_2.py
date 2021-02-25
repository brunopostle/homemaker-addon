#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Face, Cell, CellComplex, CellUtility, Topology, Graph

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list, string_to_coor, string_to_coor_2d

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
            volume = CellUtility.Volume(cell)
            planarea = cell.PlanArea()
            externalwallarea = cell.ExternalWallArea()
            crinkliness = cell.Crinkliness()

            faces_vertical = create_stl_list(Face)
            cell.FacesVertical(faces_vertical)

            faces_horizontal = create_stl_list(Face)
            cell.FacesHorizontal(faces_horizontal)

            cells_above = create_stl_list(Cell)
            cell.CellsAbove(cc, cells_above)
            if len(cells_above) == 1:
                self.assertAlmostEqual(volume, 500.0)
                self.assertAlmostEqual(planarea, 50.0)
                self.assertAlmostEqual(externalwallarea, 200.0)
                self.assertAlmostEqual(crinkliness, 4.0)
            elif len(cells_above) == 0:
                self.assertAlmostEqual(volume, 1000.0)
                self.assertAlmostEqual(planarea, 100.0)
                self.assertAlmostEqual(externalwallarea, 400.0)
                self.assertAlmostEqual(crinkliness, 4.0)

                faces_vertical = create_stl_list(Face)
                cell.FacesVertical(faces_vertical)

                for face in faces_vertical:
                    top_edges = create_stl_list(Edge)
                    bottom_edges = create_stl_list(Edge)

                    face.EdgesTop(top_edges)
                    face.EdgesBottom(bottom_edges)
                    self.assertEqual(len(top_edges), 1)
                    self.assertEqual(len(bottom_edges), 1)

                    self.assertFalse(face.FaceAbove())
                    self.assertTrue(face.FaceBelow())

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

        faces_horizontal = create_stl_list(Face)
        cc.FacesHorizontal(faces_horizontal)
        self.assertEqual(len(faces_horizontal), 5)

    def test_graph(self):
        walls = cc.Walls()
        walls_external = walls['external']
        self.assertEqual(len(walls_external), 2)
        self.assertEqual(len(walls_external[0.0]), 1)
        self.assertEqual(len(walls_external[10.0]), 1)

        lower = walls_external[0.0][10.0]
        self.assertEqual(len(lower), 1)
        self.assertEqual(len(lower[0].nodes()), 4)
        self.assertEqual(len(lower[0].edges()), 4)
        cycle = lower[0]
        self.assertTrue(cycle.is_simple_cycle())
        for node in cycle.nodes():
            self.assertEqual(string_to_coor(node)[2], 0.0)
        data = cycle.get_edge_data(['0.0__10.0__0.0','0.0__0.0__0.0'])
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0].GetType(), 1) # Vertex == 1
        self.assertEqual(data[1].GetType(), 1) # Vertex == 1
        self.assertEqual(data[2].GetType(), 8) # Face == 8
        faces2 = create_stl_list(Face)
        data[0].Faces(faces2)
        self.assertEqual(len(faces2), 3) # vertex is connected to 3 faces
        faces3 = create_stl_list(Face)
        data[2].AdjacentFaces(faces3)
        self.assertEqual(len(faces3), 6) # face is connected to 6 faces

        upper = walls_external[10.0][10.0]
        self.assertEqual(len(upper[0].nodes()), 4)
        self.assertEqual(len(upper[0].edges()), 4)

        nodes = upper[0].nodes()
        for node in nodes:
            self.assertEqual(string_to_coor(node)[2], 10.0)
            self.assertEqual(len(string_to_coor_2d(node)), 2)

        walls_internal = walls['internal'][0.0][10.0]
        for graph in walls_internal:
            self.assertEqual(len(graph.nodes()), 2)
            self.assertEqual(len(graph.edges()), 1)
            for edge in graph.edges():
                data = graph.get_edge_data(edge)
                start = data[0]
                end = data[1]
                face = data[2]
                self.assertEqual(start.X(), 10.0)
                self.assertEqual(start.Y(), 10.0)
                self.assertEqual(start.Z(), 0.0)
                self.assertEqual(end.X(), 0.0)
                self.assertEqual(end.Y(), 0.0)
                self.assertEqual(end.Z(), 0.0)

                centroid = face.Centroid()
                self.assertEqual(centroid.X(), 5.0)
                self.assertEqual(centroid.Y(), 5.0)
                self.assertEqual(centroid.Z(), 5.0)
                self.assertEqual(face.Type(), 8)

    def test_elevations(self):
        elevations = cc.Elevations()
        self.assertEqual(len(elevations), 3)
        self.assertEqual(elevations[0.0], 0)
        self.assertEqual(elevations[10.0], 1)
        self.assertEqual(elevations[20.0], 2)

    def test_connectivity(self):
        graph = Graph.ByTopology(cc, True, False, False, False, False, False, 0.0001)
        topology = graph.Topology()
        edges = create_stl_list(Edge)
        topology.Edges(edges)
        self.assertEqual(len(edges), 3)

output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()
