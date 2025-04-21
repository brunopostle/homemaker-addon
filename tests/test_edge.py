#!/usr/bin/python3

import os
import sys

from topologic_core import Vertex, Edge, Face, Cell, CellUtility

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.edge

assert topologist.edge


def test_horizontal():
    """Test horizontal edge detection"""
    point1 = Vertex.ByCoordinates(0.4, -2.2, 0.3)
    point2 = Vertex.ByCoordinates(0.5, -2.4, 0.3)
    point3 = Vertex.ByCoordinates(0.5, -2.4, 0.7)

    edge_a = Edge.ByStartVertexEndVertex(point1, point2)
    edge_b = Edge.ByStartVertexEndVertex(point3, point2)
    edge_c = Edge.ByStartVertexEndVertex(point1, point3)

    assert edge_a.IsHorizontal() is True
    assert edge_b.IsHorizontal() is False
    assert edge_c.IsHorizontal() is False


def test_vertical():
    """Test vertical edge detection"""
    point1 = Vertex.ByCoordinates(0.4, -2.2, 0.3)
    point2 = Vertex.ByCoordinates(0.5, -2.4, 0.3)
    point3 = Vertex.ByCoordinates(0.5, -2.4, 0.7)

    edge_a = Edge.ByStartVertexEndVertex(point1, point2)
    edge_b = Edge.ByStartVertexEndVertex(point3, point2)
    edge_c = Edge.ByStartVertexEndVertex(point1, point3)

    assert edge_a.IsVertical() is False
    assert edge_b.IsVertical() is True
    assert edge_c.IsVertical() is False


def test_below():
    """Test faces and cells below an edge"""
    v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
    v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
    cell = CellUtility.ByTwoCorners(v1, v2)

    edges_ptr = []
    cell.Edges(None, edges_ptr)

    faces_above = 0
    faces_below = 0
    cells_below = 0

    for edge in edges_ptr:
        if edge.IsHorizontal():
            if edge.FacesBelow(cell):
                faces_below += len(edge.FacesBelow(cell))
                assert isinstance(edge.FacesBelow(cell)[0], Face)

            if edge.FaceAbove(cell):
                faces_above += 1
                assert isinstance(edge.FaceAbove(cell), Face)

            if len(list(edge.CellsBelow(cell))) == 1:
                cells_below += 1
                assert isinstance(list(edge.CellsBelow(cell))[0], Cell)

    assert faces_above == 4
    assert faces_below == 4
    assert cells_below == 4
