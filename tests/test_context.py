#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face

assert topologist.face


class Tests(unittest.TestCase):
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

        self.vertices = []
        for point in points:
            vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
            self.vertices.append(vertex)

    def test_contents(self):
        """add edges to a cluster, self-merge, extract Wires"""
        face = Face.ByVertices([self.vertices[0], self.vertices[1], self.vertices[2]])

        # put a Face in a Topology list
        face_ptr = []
        face_ptr.append(face)

        # create an unrelated Edge
        edge = Edge.ByStartVertexEndVertex(self.vertices[3], self.vertices[4])

        # add the list containing the Face to the Edge Contents
        edge = edge.AddContents(face_ptr, 0)

        # read Contents from the Edge
        topologies_ptr = []
        edge.Contents(topologies_ptr)


if __name__ == "__main__":
    unittest.main()
