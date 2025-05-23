#!/usr/bin/python3

import os
import sys

import pytest

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face


@pytest.fixture
def setup_cellcomplex():
    """Fixture to set up the CellComplex for testing"""
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

    points.extend(
        [[0.0, 0.0, 20.0], [10.0, 0.0, 20.0], [10.0, 10.0, 20.0], [0.0, 10.0, 20.0]]
    )

    vertices = []
    for point in points:
        vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
        vertices.append(vertex)

    faces_by_vertex_id = [
        [0, 1, 2],
        [0, 2, 3],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [0, 4, 7, 3],
        [0, 1, 5, 4],
        [4, 5, 6],
        [4, 6, 7],
        [0, 2, 6, 4],
    ]

    faces_by_vertex_id.extend(
        [[4, 5, 9, 8], [5, 6, 10, 9], [6, 7, 11, 10], [7, 4, 8, 11], [8, 9, 10, 11]]
    )

    faces = []
    for face_by_id in faces_by_vertex_id:
        vertices_face = []
        for point_id in face_by_id:
            vertex = vertices[point_id]
            vertices_face.append(vertex)
        face_by_vertices = Face.ByVertices(vertices_face)
        faces.append(face_by_vertices)

    faces_ptr = []
    for face in faces:
        faces_ptr.append(face)
    return CellComplex.ByFaces(faces_ptr, 0.0001)


def test_perimeter(setup_cellcomplex):
    """Test the perimeter of cells in the CellComplex"""
    cc = setup_cellcomplex
    cells_ptr = []
    cc.Cells(None, cells_ptr)

    for cell in cells_ptr:
        perimeter = cell.Perimeter(cc)

        # Test for 3-node perimeter
        if len(perimeter.nodes()) == 3:
            assert len(perimeter.edges()) == 3
            for vertex in perimeter.nodes():
                assert perimeter.graph[vertex][1]["start_vertex"].Z() == 0.0

        # Test for 4-node perimeter
        if len(perimeter.nodes()) == 4:
            assert len(perimeter.edges()) == 4
            for vertex in perimeter.nodes():
                assert perimeter.graph[vertex][1]["start_vertex"].Z() == 10.0
