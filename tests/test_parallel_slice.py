#!/usr/bin/python3

import math
import os
import sys

import pytest
from topologic_core import Face, FaceUtility, Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.face import ParallelSlice


def square(x, y, size=4.0):
    return Face.ByVertices(
        [
            Vertex.ByCoordinates(x, y, 0.0),
            Vertex.ByCoordinates(x + size, y, 0.0),
            Vertex.ByCoordinates(x + size, y + size, 0.0),
            Vertex.ByCoordinates(x, y + size, 0.0),
        ]
    )


def offsets(edges, radians, inc):
    """Distance of each Edge from the origin, across the cutting lines, in units of inc"""
    result = []
    for edge in edges:
        for vertex in (edge.StartVertex(), edge.EndVertex()):
            distance = -vertex.X() * math.sin(radians) + vertex.Y() * math.cos(radians)
            result.append(distance / inc)
    return result


@pytest.mark.parametrize("degrees", [0, 30, 45, 60, 90, 120, 150, -30])
@pytest.mark.parametrize("position", [(0.0, 0.0), (0.7, 0.0), (0.0, 0.7), (1.3, -2.9)])
def test_cutting_lines_are_fixed_relative_to_origin(degrees, position):
    inc = 0.45
    radians = math.radians(degrees)
    faces, edges = ParallelSlice(square(*position), inc, radians)
    assert edges
    assert len(faces) == len(edges) + 1
    for offset in offsets(edges, radians, inc):
        assert offset == pytest.approx(round(offset), abs=1e-6)


@pytest.mark.parametrize("degrees", [0, 30, 45, 60, 90])
def test_cutting_lines_cover_the_face(degrees):
    inc = 0.45
    radians = math.radians(degrees)
    faces, edges = ParallelSlice(square(0.3, 0.2), inc, radians)
    # the square is 4.0 wide, the number of cuts across it depends on the angle
    width = 4.0 * (abs(math.sin(radians)) + abs(math.cos(radians)))
    assert len(edges) in (math.floor(width / inc), math.ceil(width / inc))
    assert sum(FaceUtility.Area(face) for face in faces) == pytest.approx(16.0)
