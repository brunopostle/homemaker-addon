#!/usr/bin/python3

import os
import sys
import unittest

from topologic import (
    Vertex,
    Face,
    CellComplex,
    CellUtility,
    Graph,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import string_to_coor, string_to_coor_2d


class Tests(unittest.TestCase):
    """14 faces and three cells formed by a cube sliced on the diagonal"""

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

        points.extend(
            [[0.0, 0.0, 20.0], [10.0, 0.0, 20.0], [10.0, 10.0, 20.0], [0.0, 10.0, 20.0]]
        )

        vertices = []
        for point in points:
            vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
            vertices.append(vertex)

        faces_by_vertex_id = [
            [0, 1, 2],
            [0, 2, 3],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [0, 4, 7, 3],
            [0, 1, 5, 4],
            [4, 5, 6],
            [4, 6, 7],
            [0, 2, 6, 4],
        ]

        faces_by_vertex_id.extend(
            [[4, 5, 9, 8], [5, 6, 10, 9], [6, 7, 11, 10], [7, 4, 8, 11], [8, 9, 10, 11]]
        )

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
        self.cc.Faces(all_faces_ptr)
        self.assertEqual(len(all_faces_ptr), 14)
        for face in all_faces_ptr:
            cells_ptr = face.Cells_Cached(self.cc)
            self.assertGreater(len(cells_ptr), 0)
            self.assertLess(len(cells_ptr), 3)

        vertical_faces_ptr = []
        self.cc.FacesVertical(vertical_faces_ptr)
        self.assertEqual(len(vertical_faces_ptr), 9)
        for face in vertical_faces_ptr:
            self.assertTrue(face.IsVertical())

        horizontal_faces_ptr = []
        self.cc.FacesHorizontal(horizontal_faces_ptr)
        self.assertEqual(len(horizontal_faces_ptr), 5)
        for face in horizontal_faces_ptr:
            self.assertTrue(face.IsHorizontal())

    def test_cells(self):

        centroid = self.cc.Centroid()
        self.assertEqual(centroid.X(), 5.0)
        self.assertEqual(centroid.Y(), 5.0)
        self.assertEqual(centroid.Z(), 10.0)

        cells_ptr = []
        self.cc.Cells(cells_ptr)
        self.assertEqual(len(cells_ptr), 3)

        for cell in cells_ptr:
            centroid = cell.Centroid()
            volume = CellUtility.Volume(cell)
            planarea = cell.PlanArea()
            externalwallarea = cell.ExternalWallArea(self.cc)
            crinkliness = cell.Crinkliness(self.cc)

            vertical_faces_ptr = []
            cell.FacesVertical(vertical_faces_ptr)

            horizontal_faces_ptr = []
            cell.FacesHorizontal(horizontal_faces_ptr)

            above_cells_ptr = []
            cell.CellsAbove(self.cc, above_cells_ptr)
            if len(above_cells_ptr) == 1:
                self.assertAlmostEqual(volume, 500.0)
                self.assertAlmostEqual(planarea, 50.0)
                self.assertAlmostEqual(externalwallarea, 200.0)
                self.assertAlmostEqual(crinkliness, 4.0)
                cell.Set("usage", "Kitchen")
            elif len(above_cells_ptr) == 0:
                self.assertAlmostEqual(volume, 1000.0)
                self.assertAlmostEqual(planarea, 100.0)
                self.assertAlmostEqual(externalwallarea, 400.0)
                self.assertAlmostEqual(crinkliness, 4.0)
                cell.Set("usage", "Bedroom")

                vertical_faces_ptr = []
                cell.FacesVertical(vertical_faces_ptr)

                for face in vertical_faces_ptr:
                    top_edges_ptr = []
                    bottom_edges_ptr = []

                    face.EdgesTop(top_edges_ptr)
                    face.EdgesBottom(bottom_edges_ptr)
                    self.assertEqual(len(top_edges_ptr), 1)
                    self.assertEqual(len(bottom_edges_ptr), 1)

                    self.assertFalse(face.FaceAbove(self.cc))
                    self.assertTrue(face.FaceBelow(self.cc))

            below_cells_ptr = []
            cell.CellsBelow(self.cc, below_cells_ptr)
            if len(below_cells_ptr) == 2:
                self.assertAlmostEqual(volume, 1000.0)
                self.assertEqual(cell.Usage(), "Bedroom")
            elif len(below_cells_ptr) == 0:
                self.assertAlmostEqual(volume, 500.0)
                self.assertEqual(cell.Usage(), "Kitchen")

        cells_ptr = []
        self.cc.Cells(cells_ptr)
        has_kitchen = False
        has_bedroom = False
        for cell in cells_ptr:
            if cell.Usage() == "Bedroom":
                has_bedroom = True
            if cell.Usage() == "Kitchen":
                has_kitchen = True
        self.assertTrue(has_bedroom)
        self.assertTrue(has_kitchen)

    def test_faces(self):
        vertical_faces_ptr = []
        self.cc.FacesVertical(vertical_faces_ptr)
        self.assertEqual(len(vertical_faces_ptr), 9)

        horizontal_faces_ptr = []
        self.cc.FacesHorizontal(horizontal_faces_ptr)
        self.assertEqual(len(horizontal_faces_ptr), 5)

    def test_graph(self):
        traces, hulls, normals, elevations = self.cc.GetTraces()
        traces_external = traces["external"]
        self.assertEqual(len(traces_external), 2)
        self.assertEqual(len(traces_external[0.0]), 1)
        self.assertEqual(len(traces_external[10.0]), 1)

        lower = traces_external[0.0][10.0]["default"]
        self.assertEqual(len(lower), 1)
        self.assertEqual(len(lower[0].nodes()), 4)
        self.assertEqual(len(lower[0].edges()), 4)
        cycle = lower[0]
        self.assertTrue(cycle.is_simple_cycle())
        for node in cycle.nodes():
            self.assertEqual(string_to_coor(node)[2], 0.0)
        data = cycle.get_edge_data(["0.0__10.0__0.0", "0.0__0.0__0.0"])
        self.assertEqual(len(data), 5)
        # self.assertEqual(data[0].GetType(), 1)  # Vertex == 1
        # self.assertEqual(data[1].GetType(), 1)  # Vertex == 1
        # self.assertEqual(data[2].GetType(), 8)  # Face == 8
        # self.assertEqual(data[3].GetType(), 32)  # Cell == 32
        self.assertEqual(data[4], None)  # no outer Cell
        faces_ptr = data[0].Faces_Cached(self.cc)
        self.assertEqual(len(faces_ptr), 3)  # vertex is connected to 3 faces
        faces_ptr = []
        data[2].AdjacentFaces(self.cc, faces_ptr)
        self.assertEqual(len(faces_ptr), 6)  # face is connected to 6 faces

        upper = traces_external[10.0][10.0]["default"]
        self.assertEqual(len(upper[0].nodes()), 4)
        self.assertEqual(len(upper[0].edges()), 4)

        nodes = upper[0].nodes()
        for node in nodes:
            self.assertEqual(string_to_coor(node)[2], 10.0)
            self.assertEqual(len(string_to_coor_2d(node)), 2)

        traces_internal = traces["internal"][0.0][10.0]["default"]
        for graph in traces_internal:
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
        traces, hulls, normals, elevations = self.cc.GetTraces()
        self.assertEqual(len(elevations), 3)
        self.assertEqual(elevations[0.0], 0)
        self.assertEqual(elevations[10.0], 1)
        self.assertEqual(elevations[20.0], 2)

    def test_connectivity(self):
        graph = Graph.ByTopology(
            self.cc, True, False, False, False, False, False, 0.0001
        )
        topology = graph.Topology()
        edges_ptr = []
        topology.Edges(edges_ptr)
        self.assertEqual(len(edges_ptr), 3)


if __name__ == "__main__":
    unittest.main()
