#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Face, Cell, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face

assert topologist.face


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
        # Give every Cell and Face an index number
        self.cc.IndexTopology()

    def test_vertices(self):
        graph = self.cc.Adjacency()

        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        self.assertEqual(len(vertices_ptr), 6)
        for vertex in vertices_ptr:
            if vertex.Get("class") == "Face":
                self.assertFalse(vertex.Get("index") is None)
            elif vertex.Get("class") == "Cell":
                self.assertFalse(vertex.Get("index") is None)
            else:
                self.assertTrue(False)

    def test_faces(self):
        graph = self.cc.Adjacency()
        faces = graph.Faces(self.cc)
        # only three of the fourteen faces are represented in the graph
        self.assertEqual(len(faces), 3)
        for face in faces:
            self.assertEqual(type(face), Face)
            # this Face has to have a Vertex in the Graph, that represents a Face
            vertex = face.GraphVertex(graph)
            self.assertEqual(type(vertex), Vertex)
            self.assertEqual(vertex.Get("class"), "Face")
            # it should be the same Face
            entity = graph.GetEntity(self.cc, vertex)
            self.assertTrue(face.IsSame(entity))

    def test_cells(self):
        graph = self.cc.Adjacency()
        cells = graph.Cells(self.cc)
        self.assertEqual(len(cells), 3)
        for cell in cells:
            self.assertEqual(type(cell), Cell)

    def test_graphvertex(self):
        graph = self.cc.Adjacency()
        cells_ptr = []
        self.cc.Cells(None, cells_ptr)
        self.assertEqual(len(cells_ptr), 3)
        for cell in cells_ptr:
            # vertex is the node in the Graph that corresponds to this Cell
            vertex = cell.GraphVertex(graph)
            # it should be a Vertex, representing a Cell
            self.assertEqual(type(vertex), Vertex)
            self.assertEqual(vertex.Get("class"), "Cell")
            # the equivalent entity in the CellComplex, should be a Cell
            entity = graph.GetEntity(self.cc, vertex)
            self.assertEqual(type(entity), Cell)
            # it should be the same Cell we started with
            self.assertTrue(cell.IsSame(entity))

    def test_graphvertex2(self):
        graph = self.cc.Adjacency()
        faces_ptr = []
        self.cc.Faces(None, faces_ptr)
        self.assertEqual(len(faces_ptr), 14)
        for face in faces_ptr:
            # vertex is the node in the Graph that corresponds to this Face
            vertex = face.GraphVertex(graph)
            # the Graph may not have a node for this Face (e.g. purged, external wall)
            if vertex is None:
                continue
            # it should be a Vertex, representing a Face
            self.assertEqual(type(vertex), Vertex)
            self.assertEqual(vertex.Get("class"), "Face")
            # the equivalent entity in the CellComplex, should be a Face
            entity = graph.GetEntity(self.cc, vertex)
            self.assertEqual(type(entity), Face)
            # it should be the same Face we started with
            self.assertTrue(face.IsSame(entity))

    def test_isconnected(self):
        graph = self.cc.Adjacency()
        self.assertTrue(graph.IsConnected())

    def test_circulation(self):
        graph = self.cc.Adjacency()

        # 3 faces and 3 cells = 6 vertices
        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        self.assertEqual(len(vertices_ptr), 6)

        edges_ptr = []
        graph.Edges(edges_ptr)
        self.assertEqual(len(edges_ptr), 6)

        graph.Circulation(self.cc)

        # 2 horizontal faces removed = 4 vertices
        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        self.assertEqual(len(vertices_ptr), 4)

        edges_ptr = []
        graph.Edges(edges_ptr)
        self.assertEqual(len(edges_ptr), 2)

        self.assertFalse(graph.IsConnected())
        dot = graph.Dot(self.cc)
        self.assertTrue(type(dot) == str)

    def test_shortest_path(self):
        graph = self.cc.Adjacency()
        table = graph.ShortestPathTable()
        self.assertEqual(table["0"]["2"], table["2"]["0"])
        self.assertEqual(table["1"]["2"], table["2"]["1"])
        self.assertEqual(table["1"]["0"], table["0"]["1"])

    def test_separation(self):
        graph = self.cc.Adjacency()
        table = graph.ShortestPathTable()
        graph.Separation(table, self.cc)
        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        for vertex in vertices_ptr:
            if vertex.Get("class") == "Cell":
                self.assertTrue(float(vertex.Get("separation")) > 0.0)


if __name__ == "__main__":
    unittest.main()
