#!/usr/bin/python3

import os
import sys
import pytest

from topologic_core import (
    Vertex,
    Face,
    EdgeUtility,
    FaceUtility,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.geometry import (
    x_product_3d,
    normalise_3d,
    magnitude_3d,
    scale_3d,
    subtract_3d,
    add_3d,
    distance_3d,
)


@pytest.fixture
def face():
    return Face.ByVertices(
        [
            Vertex.ByCoordinates(1.0, 2.0, 0.0),
            Vertex.ByCoordinates(5.0, 2.0, 0.0),
            Vertex.ByCoordinates(5.0, 2.0, 4.0),
            Vertex.ByCoordinates(4.0, 2.0, 3.0),
            Vertex.ByCoordinates(3.0, 2.0, 4.0),
            Vertex.ByCoordinates(1.0, 2.0, 4.0),
        ]
    )


def test_faces(face):
    assert FaceUtility.Area(face) == 15.0

    top_edge_ptr = []
    face.EdgesTop(top_edge_ptr)

    bottom_edge_ptr = []
    face.EdgesBottom(bottom_edge_ptr)

    crop_edge_ptr = []
    face.EdgesCrop(crop_edge_ptr)

    assert len(top_edge_ptr) == 1
    assert len(bottom_edge_ptr) == 1
    assert len(crop_edge_ptr) == 2

    assert EdgeUtility.Length(crop_edge_ptr[0]) ** 2 == pytest.approx(2)
    assert EdgeUtility.Length(crop_edge_ptr[1]) ** 2 == pytest.approx(2)


def test_plane(face):
    crop_edge_ptr = []
    face.EdgesCrop(crop_edge_ptr)
    edge0 = crop_edge_ptr[0]
    start = edge0.StartVertex().Coordinates()
    end = edge0.EndVertex().Coordinates()
    vector = subtract_3d(end, start)
    perp_2d = [0 - vector[1], vector[0], 0.0]
    xprod = x_product_3d(vector, perp_2d)

    assert xprod[0] == pytest.approx(-0.707106781)
    assert xprod[1] == pytest.approx(0.0)
    assert xprod[2] == pytest.approx(0.707106781)


def test_math():
    assert distance_3d([1.0, 0.0, 1.0], [1.0, 3.0, 5.0]) == 5.0
    assert scale_3d([1.0, 2.0, 3.0], 2.0) == [2.0, 4.0, 6.0]
    assert scale_3d(-2.0, [1.0, 2.0, 3.0]) == [-2.0, -4.0, -6.0]
    assert magnitude_3d([3.0, 4.0, 0.0]) == 5.0
    assert normalise_3d([0.0, 4.0, 0.0]) == [0.0, 1.0, 0.0]
    assert normalise_3d([0.0, 0.0, 0.0]) == [1.0, 0.0, 0.0]
    assert x_product_3d([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == [0.0, 0.0, 1.0]
    assert add_3d([1.0, 2.0, 3.0], [5.0, 3.0, 1.0]) == [6.0, 5.0, 4.0]
    assert subtract_3d([1.0, 2.0, 3.0], [5.0, 3.0, 1.0]) == [-4.0, -1.0, 2.0]
