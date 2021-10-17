#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Topology, Vertex, Edge, Wire, Cluster

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import create_stl_list, el


class Tests(unittest.TestCase):
    def setUp(self):
        # a closed loop
        points = [
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 10.0, 0.0],
            [0.0, 10.0, 0.0],
        ]
        # an open chain
        points.extend([[0.0, 0.0, 20.0], [10.0, 0.0, 20.0], [10.0, 10.0, 20.0]])

        vertices = []
        for point in points:
            vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
            vertices.append(vertex)

        # anti-clockwise
        self.edge_0 = Edge.ByStartVertexEndVertex(vertices[0], vertices[1])
        self.edge_1 = Edge.ByStartVertexEndVertex(vertices[1], vertices[2])
        self.edge_2 = Edge.ByStartVertexEndVertex(vertices[2], vertices[3])
        self.edge_3 = Edge.ByStartVertexEndVertex(vertices[3], vertices[0])

        # clockwise
        self.edge_4 = Edge.ByStartVertexEndVertex(vertices[3], vertices[2])
        self.edge_5 = Edge.ByStartVertexEndVertex(vertices[2], vertices[1])
        self.edge_6 = Edge.ByStartVertexEndVertex(vertices[1], vertices[0])
        self.edge_7 = Edge.ByStartVertexEndVertex(vertices[0], vertices[3])

        # open chain
        self.edge_8 = Edge.ByStartVertexEndVertex(vertices[4], vertices[5])
        self.edge_9 = Edge.ByStartVertexEndVertex(vertices[5], vertices[6])

    def test_cluster(self):
        """add edges to a cluster, self-merge, extract Wires"""
        edges_ptr = create_stl_list(Topology)
        edges_ptr.push_back(self.edge_2)
        edges_ptr.push_back(self.edge_1)
        edges_ptr.push_back(self.edge_0)
        edges_ptr.push_back(self.edge_3)
        edges_ptr.push_back(self.edge_8)
        edges_ptr.push_back(self.edge_9)
        cluster = Cluster.ByTopologies(edges_ptr)
        merged = cluster.SelfMerge()
        wires_ptr = create_stl_list(Wire)
        merged.Wires(wires_ptr)
        for wire in wires_ptr:
            vertices_ptr = create_stl_list(Vertex)
            wire.Vertices(vertices_ptr)
            if len(list(vertices_ptr)) == 4:
                self.assertTrue(wire.IsClosed())
            if len(list(vertices_ptr)) == 3:
                self.assertFalse(wire.IsClosed())

    def test_anticlockwise(self):
        """Four points, three segments, anti-clockwise"""
        edges_ptr = create_stl_list(Edge)
        edges_ptr.push_back(self.edge_2)
        edges_ptr.push_back(self.edge_1)
        edges_ptr.push_back(self.edge_0)
        wire = Wire.ByEdges(edges_ptr)
        self.assertFalse(wire.IsClosed())

        vertices_ptr = create_stl_list(Vertex)
        wire.Vertices(vertices_ptr)
        vertices = list(vertices_ptr)
        self.assertEqual(vertices[0].X(), 0.0)
        self.assertEqual(vertices[0].Y(), 0.0)
        self.assertEqual(vertices[1].X(), 10.0)
        self.assertEqual(vertices[1].Y(), 0.0)
        self.assertEqual(vertices[2].X(), 10.0)
        self.assertEqual(vertices[2].Y(), 10.0)
        self.assertEqual(vertices[3].X(), 0.0)
        self.assertEqual(vertices[3].Y(), 10.0)

    def test_clockwise(self):
        """Four points, three segments, clockwise"""
        edges_ptr = create_stl_list(Edge)
        edges_ptr.push_back(self.edge_6)
        edges_ptr.push_back(self.edge_4)
        edges_ptr.push_back(self.edge_5)
        wire = Wire.ByEdges(edges_ptr)
        self.assertFalse(wire.IsClosed())

        vertices_ptr = create_stl_list(Vertex)
        wire.Vertices(vertices_ptr)
        vertices = list(vertices_ptr)
        self.assertEqual(vertices[0].X(), 0.0)
        self.assertEqual(vertices[0].Y(), 10.0)
        self.assertEqual(vertices[1].X(), 10.0)
        self.assertEqual(vertices[1].Y(), 10.0)
        self.assertEqual(vertices[2].X(), 10.0)
        self.assertEqual(vertices[2].Y(), 0.0)
        self.assertEqual(vertices[3].X(), 0.0)
        self.assertEqual(vertices[3].Y(), 0.0)

    def test_clockwise_closed(self):
        """Four points, four segments, clockwise"""
        edges_ptr = create_stl_list(Edge)
        edges_ptr.push_back(self.edge_6)
        edges_ptr.push_back(self.edge_4)
        edges_ptr.push_back(self.edge_7)
        edges_ptr.push_back(self.edge_5)
        wire = Wire.ByEdges(edges_ptr)
        self.assertTrue(wire.IsClosed())

        vertices_ptr = create_stl_list(Vertex)
        wire.Vertices(vertices_ptr)
        vertices = list(vertices_ptr)
        self.assertEqual(vertices[0].X(), 10.0)
        self.assertEqual(vertices[0].Y(), 0.0)
        self.assertEqual(vertices[1].X(), 0.0)
        self.assertEqual(vertices[1].Y(), 0.0)
        self.assertEqual(vertices[2].X(), 0.0)
        self.assertEqual(vertices[2].Y(), 10.0)
        self.assertEqual(vertices[3].X(), 10.0)
        self.assertEqual(vertices[3].Y(), 10.0)

    def test_el(self):
        self.assertEqual(el(3.99999), 4.0)
        self.assertEqual(el(-3.99999), -4.0)
        self.assertEqual(el(4.00001), 4.0)
        self.assertEqual(el(-4.00001), -4.0)
        self.assertEqual(el(0.00001), 0.0)
        self.assertEqual(el(-0.00001), 0.0)


if __name__ == "__main__":
    unittest.main()
