#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Face, Cell, CellComplex, Graph

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import create_stl_list


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

        faces_ptr = create_stl_list(Face)
        for face in faces:
            faces_ptr.push_back(face)
        self.cc = CellComplex.ByFaces(faces_ptr, 0.0001)

    def test_vertices(self):
        graph = Graph.Adjacency(self.cc)

        vertices = create_stl_list(Vertex)
        graph.Vertices(vertices)
        self.assertEqual(len(vertices), 6)
        for vertex in vertices:
            if vertex.Get("class") == "Face":
                self.assertFalse(vertex.Get("index") == None)
            elif vertex.Get("class") == "Cell":
                self.assertFalse(vertex.Get("index") == None)
            else:
                self.assertTrue(False)

    def test_faces(self):
        graph = Graph.Adjacency(self.cc)
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
        graph = Graph.Adjacency(self.cc)
        cells = graph.Cells(self.cc)
        self.assertEqual(len(cells), 3)
        for cell in cells:
            self.assertEqual(type(cell), Cell)

    def test_graphvertex(self):
        graph = Graph.Adjacency(self.cc)
        cells = create_stl_list(Cell)
        self.cc.Cells(cells)
        self.assertEqual(len(cells), 3)
        for cell in cells:
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
        graph = Graph.Adjacency(self.cc)
        faces = create_stl_list(Face)
        self.cc.Faces(faces)
        self.assertEqual(len(faces), 14)
        for face in faces:
            # vertex is the node in the Graph that corresponds to this Face
            vertex = face.GraphVertex(graph)
            # the Graph may not have a node for this Face (e.g. purged, external wall)
            if vertex == None:
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
        graph = Graph.Adjacency(self.cc)
        self.assertTrue(graph.IsConnected())

    def test_circulation(self):
        graph = Graph.Adjacency(self.cc)

        # 3 faces and 3 cells = 6 vertices
        vertices = create_stl_list(Vertex)
        graph.Vertices(vertices)
        self.assertEqual(len(vertices), 6)

        edges = create_stl_list(Edge)
        graph.Edges(edges)
        self.assertEqual(len(edges), 6)

        graph.Circulation(self.cc)

        # 2 horizontal faces removed = 4 vertices
        vertices = create_stl_list(Vertex)
        graph.Vertices(vertices)
        self.assertEqual(len(vertices), 4)

        edges = create_stl_list(Edge)
        graph.Edges(edges)
        self.assertEqual(len(edges), 2)

        self.assertFalse(graph.IsConnected())
        dot = graph.Dot(self.cc)
        self.assertTrue(type(dot) == str)


if __name__ == "__main__":
    unittest.main()
