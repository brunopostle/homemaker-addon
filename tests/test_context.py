#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Face, Topology

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list, fixTopologyClass

points = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0],
          [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [10.0, 10.0, 10.0], [0.0, 10.0, 10.0]]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

faces_by_vertex_id = [[0, 1, 2], [0, 2, 3], [1, 2, 6, 5], [2, 3, 7, 6], [0, 4, 7, 3],
                      [0, 1, 5, 4], [4, 5, 6], [4, 6, 7], [0, 2, 6, 4]]

class Tests(unittest.TestCase):
    def test_contents(self):
        """add edges to a cluster, self-merge, extract Wires"""
        face = Face.ByVertices([vertices[0], vertices[1], vertices[2]])

        # put a Face in a Topology list
        face_ptr = create_stl_list(Topology)
        face_ptr.push_back(face)

        # create an unrelated Edge
        edge = Edge.ByStartVertexEndVertex(vertices[3], vertices[4])

        # add the list containing the Face to the Edge Contents
        edge = edge.AddContents(face_ptr, 0)

        # read Contents from the Edge
        contents = create_stl_list(Topology)
        edge.Contents(contents)

        for topology in contents:
            fixTopologyClass(topology)
            self.assertEqual(topology.Type(), 8)

if __name__ == '__main__':
    unittest.main()
