#!/usr/bin/python3

import os
import sys

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.face

assert topologist.face


def test_faces():
    """Test creating six faces of a cube"""
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

    vertices = []
    for point in points:
        vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
        vertices.append(vertex)

    faces_by_vertex_id = [
        [0, 1, 2, 3],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [0, 4, 7, 3],
        [0, 1, 5, 4],
        [4, 5, 6, 7],
    ]

    faces_ptr = []
    for face_by_id in faces_by_vertex_id:
        vertices_face = []
        for point_id in face_by_id:
            vertex = vertices[point_id]
            vertices_face.append(vertex)

        face = Face.ByVertices(vertices_face)
        face.Set("stylename", "orange")
        faces_ptr.append(face)

    cellcomplex = CellComplex.ByFaces(faces_ptr, 0.0001)
    cellcomplex.ApplyDictionary(faces_ptr)

    # Check number of faces
    assert len(faces_ptr) == 6

    # Check style name for each face
    for face in faces_ptr:
        assert face.Get("stylename") == "orange"


def test_faces_cellcomplex():
    """Test faces within a cell complex"""
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

    vertices = []
    for point in points:
        vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
        vertices.append(vertex)

    faces_by_vertex_id = [
        [0, 1, 2, 3],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [0, 4, 7, 3],
        [0, 1, 5, 4],
        [4, 5, 6, 7],
    ]

    faces_ptr = []
    for face_by_id in faces_by_vertex_id:
        vertices_face = []
        for point_id in face_by_id:
            vertex = vertices[point_id]
            vertices_face.append(vertex)

        face = Face.ByVertices(vertices_face)
        face.Set("stylename", "orange")
        faces_ptr.append(face)

    cellcomplex = CellComplex.ByFaces(faces_ptr, 0.0001)
    cellcomplex.ApplyDictionary(faces_ptr)

    faces_in_complex = []
    cellcomplex.Faces(None, faces_in_complex)

    # Check number of faces
    assert len(faces_in_complex) == 6

    # Check vertical faces
    for face in faces_in_complex:
        if not face.IsVertical():
            continue
        assert face.Get("stylename") == "orange"
