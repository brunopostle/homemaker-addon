#!/usr/bin/python3

import os
import sys
import pytest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.geometry import (
    add_2d,
    angle_2d,
    distance_2d,
    normalise_2d,
    points_2line,
    line_intersection,
    transform,
    map_to_2d,
    map_to_2d_simple,
    normal_by_perimeter,
)
import topologist

assert topologist
from topologic_core import Face, Vertex


def test_transform():
    identity_matrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    scale_matrix = np.array([[2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0], [0, 0, 0, 2]])
    assert transform(identity_matrix, [2, 3, 4]) == [2, 3, 4]
    assert transform(scale_matrix, [2, 3, 4]) == [4, 6, 8]
    assert transform(identity_matrix, [2, 3]) == [2, 3]
    assert transform(scale_matrix, [2, 3]) == [4, 6]


def test_add_2d():
    assert add_2d([2, 3], [5, -3]) == [7.0, 0]
    assert add_2d([2.0, 3], [5, -3.0]) == [7.0, 0]


def test_angle_2d():
    assert angle_2d([2, 0], [5, 0]) == 0
    assert pytest.approx(angle_2d([5, 0], [2, 0]), abs=1e-8) == 3.14159265
    assert pytest.approx(angle_2d([2, -5], [2, 7]), abs=1e-8) == 1.57079632
    assert pytest.approx(angle_2d([2, 7], [2, -5]), abs=1e-8) == -1.57079632


def test_distance_2d():
    assert distance_2d([0, 0], [3, 4]) == 5
    assert distance_2d([1, -1], [-3, 2]) == 5


def test_normalise_2d():
    assert normalise_2d([3, 4]) == [0.6, 0.8]
    assert normalise_2d([-3, 4]) == [-0.6, 0.8]
    assert normalise_2d([0, 0]) == [1, 0]


def test_points_2line():
    line = points_2line([1, 1], [2, 2])
    assert line["a"] == 1
    assert line["b"] == 0

    line2 = points_2line([3, 0], [3, 5])
    point = line_intersection(line, line2)
    assert pytest.approx(point[0]) == 3
    assert pytest.approx(point[1]) == 3

    line3 = points_2line([4, 0], [4, 5])
    point = line_intersection(line2, line3)
    assert point is None


def test_map_to_2d():
    # returns a 2d polygon, a matrix to map from 2d back to 3d, and a normal representing the original vertical
    polygon3d = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    normal = [0, 0, 1]

    polygon2d, matrix, normal_result = map_to_2d(polygon3d, normal)
    assert normal_result == matrix[:, 2][0:3].tolist()
    polygon2d_a, matrix_a = map_to_2d_simple(polygon3d, normal)
    assert normal == matrix_a[:, 2][0:3].tolist()

    polygon3d = [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]]
    normal = [0, 0, -1]

    polygon2d, matrix, normal_result = map_to_2d(polygon3d, normal)
    assert normal_result == matrix[:, 2][0:3].tolist()
    polygon2d_a, matrix_a = map_to_2d_simple(polygon3d, normal)
    assert normal == matrix_a[:, 2][0:3].tolist()

    polygon3d = [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]]
    normal = [0, -1, 0]

    polygon2d, matrix, normal_result = map_to_2d(polygon3d, normal)
    assert normal_result == matrix[:, 2][0:3].tolist()
    polygon2d_a, matrix_a = map_to_2d_simple(polygon3d, normal)
    assert normal == matrix_a[:, 2][0:3].tolist()


def test_normal():
    polygon3d = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [0, 0, 1], [1, 0, 1], [1, 0, 0]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)

    polygon3d = [[0, 0, 0], [0, 0, 1], [0, 0, 2], [0, 1, 0]]
    face = Face.ByVertices([Vertex.ByCoordinates(*node) for node in polygon3d])
    assert face.Normal() == normal_by_perimeter(polygon3d)


if __name__ == "__main__":
    pytest.main()
