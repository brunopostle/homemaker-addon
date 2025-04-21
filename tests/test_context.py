#!/usr/bin/python3

import os
import sys
import pytest

from topologic_core import Vertex, Edge, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face

assert topologist.face


@pytest.fixture
def vertices():
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

    return [Vertex.ByCoordinates(point[0], point[1], point[2]) for point in points]


def test_contents(vertices):
    """add edges to a cluster, self-merge, extract Wires"""
    face = Face.ByVertices([vertices[0], vertices[1], vertices[2]])

    # put a Face in a Topology list
    face_ptr = [face]

    # create an unrelated Edge
    edge = Edge.ByStartVertexEndVertex(vertices[3], vertices[4])

    # add the list containing the Face to the Edge Contents
    edge = edge.AddContents(face_ptr, 0)

    # read Contents from the Edge
    topologies_ptr = []
    edge.Contents(topologies_ptr)
