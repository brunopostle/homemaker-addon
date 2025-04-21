#!/usr/bin/python3

import os
import sys
import pytest

from topologic_core import Vertex, Edge, Wire, Cluster

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import el


@pytest.fixture
def vertices_and_edges():
    """Prepare vertices and edges for testing"""
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

    # Prepare edges
    edges = {
        # anti-clockwise
        "edge_0": Edge.ByStartVertexEndVertex(vertices[0], vertices[1]),
        "edge_1": Edge.ByStartVertexEndVertex(vertices[1], vertices[2]),
        "edge_2": Edge.ByStartVertexEndVertex(vertices[2], vertices[3]),
        "edge_3": Edge.ByStartVertexEndVertex(vertices[3], vertices[0]),
        # clockwise
        "edge_4": Edge.ByStartVertexEndVertex(vertices[3], vertices[2]),
        "edge_5": Edge.ByStartVertexEndVertex(vertices[2], vertices[1]),
        "edge_6": Edge.ByStartVertexEndVertex(vertices[1], vertices[0]),
        "edge_7": Edge.ByStartVertexEndVertex(vertices[0], vertices[3]),
        # open chain
        "edge_8": Edge.ByStartVertexEndVertex(vertices[4], vertices[5]),
        "edge_9": Edge.ByStartVertexEndVertex(vertices[5], vertices[6]),
    }

    return vertices, edges


def test_cluster(vertices_and_edges):
    """Test cluster merging and wire extraction"""
    _, edges = vertices_and_edges
    edges_ptr = [
        edges["edge_2"],
        edges["edge_1"],
        edges["edge_0"],
        edges["edge_3"],
        edges["edge_8"],
        edges["edge_9"],
    ]
    cluster = Cluster.ByTopologies(edges_ptr)
    merged = cluster.SelfMerge()

    wires_ptr = []
    merged.Wires(None, wires_ptr)

    for wire in wires_ptr:
        vertices_ptr = []
        wire.Vertices(None, vertices_ptr)

        if len(vertices_ptr) == 4:
            assert wire.IsClosed() is True
        if len(vertices_ptr) == 3:
            assert wire.IsClosed() is False


def test_anticlockwise(vertices_and_edges):
    """Four points, three segments, anti-clockwise"""
    _, edges = vertices_and_edges
    edges_ptr = [edges["edge_2"], edges["edge_1"], edges["edge_0"]]
    wire = Wire.ByEdges(edges_ptr)

    # In the original test, this was expected to be NOT closed
    assert wire.IsClosed() is False

    vertices_ptr = []
    wire.Vertices(None, vertices_ptr)

    assert vertices_ptr[0].X() == 0.0
    assert vertices_ptr[0].Y() == 0.0
    assert vertices_ptr[1].X() == 10.0
    assert vertices_ptr[1].Y() == 0.0
    assert vertices_ptr[2].X() == 10.0
    assert vertices_ptr[2].Y() == 10.0
    assert vertices_ptr[3].X() == 0.0
    assert vertices_ptr[3].Y() == 10.0


def test_clockwise(vertices_and_edges):
    """Four points, three segments, clockwise"""
    _, edges = vertices_and_edges
    edges_ptr = [edges["edge_6"], edges["edge_4"], edges["edge_5"]]
    wire = Wire.ByEdges(edges_ptr)

    # In the original test, this was expected to be NOT closed
    assert wire.IsClosed() is False

    vertices_ptr = []
    wire.Vertices(None, vertices_ptr)

    assert vertices_ptr[0].X() == 0.0
    assert vertices_ptr[0].Y() == 10.0
    assert vertices_ptr[1].X() == 10.0
    assert vertices_ptr[1].Y() == 10.0
    assert vertices_ptr[2].X() == 10.0
    assert vertices_ptr[2].Y() == 0.0
    assert vertices_ptr[3].X() == 0.0
    assert vertices_ptr[3].Y() == 0.0


def test_clockwise_closed(vertices_and_edges):
    """Four points, four segments, clockwise"""
    _, edges = vertices_and_edges
    edges_ptr = [edges["edge_6"], edges["edge_4"], edges["edge_7"], edges["edge_5"]]
    wire = Wire.ByEdges(edges_ptr)

    # This wire should be closed
    assert wire.IsClosed() is True

    vertices_ptr = []
    wire.Vertices(None, vertices_ptr)

    assert vertices_ptr[0].X() == 10.0
    assert vertices_ptr[0].Y() == 0.0
    assert vertices_ptr[1].X() == 0.0
    assert vertices_ptr[1].Y() == 0.0
    assert vertices_ptr[2].X() == 0.0
    assert vertices_ptr[2].Y() == 10.0
    assert vertices_ptr[3].X() == 10.0
    assert vertices_ptr[3].Y() == 10.0


@pytest.mark.parametrize(
    "input_value, expected",
    [
        (3.99999, 4.0),
        (-3.99999, -4.0),
        (4.00001, 4.0),
        (-4.00001, -4.0),
        (0.00001, 0.0),
        (-0.00001, 0.0),
    ],
)
def test_el(input_value, expected):
    """Test edge-length rounding function"""
    assert el(input_value) == expected
