#!/usr/bin/python3

import pytest
from topologic_core import Vertex, CellUtility


@pytest.fixture
def cell_and_points():
    v1 = Vertex.ByCoordinates(-0.58055890, -3.2437859, 2.1412814)
    v2 = Vertex.ByCoordinates(2.5558017, -0.65540771, 4.0045023)
    cell = CellUtility.ByTwoCorners(v1, v2)

    point1 = Vertex.ByCoordinates(0.41215598, -2.0419712, 0.31666728)
    point2 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.31666728)
    point3 = Vertex.ByCoordinates(0.41215598, -2.0419712, 2.1412814)

    return cell, point1, point2, point3


def test_contains(cell_and_points):
    """0 == INSIDE, 1 = ON_BOUNDARY, 2 = OUTSIDE"""
    cell, point1, point2, point3 = cell_and_points

    assert CellUtility.Contains(cell, point1, 0.001) == 2
    assert CellUtility.Contains(cell, point2, 0.001) == 0
    assert CellUtility.Contains(cell, point3, 0.001) == 1
