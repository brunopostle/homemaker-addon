#!/usr/bin/python3

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from topologic_core import Vertex, Face, CellComplex, CellUtility, Topology
import topologist


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
cc = CellComplex.ByFaces(faces_ptr, 0.0001)


def test_upward():
    _vertices = []
    cc.Vertices(None, _vertices)
    cells = _vertices[0].Cells_Cached(cc)
    assert len(cells) == 2


def test_vertices():
    assert points[0][0] == 0.0
    assert points[1][0] == 10.0


def test_vertices_cc():
    assert len(points) == len(vertices)
    assert vertices[0].X() == 0.0
    assert vertices[1].X() == 10.0
    assert vertices[-1].Y() == 10.0


def test_faces():
    assert len(faces_by_vertex_id) == len(faces)
    assert faces_by_vertex_id[0][2] == 2
    assert faces[0].IsHorizontal()
    assert not faces[0].IsVertical()
    assert faces[2].IsVertical()
    assert faces[-1].IsVertical()


def test_faces_cc():
    faces_ptr = []
    cc.Faces(None, faces_ptr)
    assert len(faces_ptr) == 9

    for face in faces_ptr:
        cells_ptr = face.Cells_Cached(cc)
        assert len(cells_ptr) > 0
        assert len(cells_ptr) < 3

    vertical_faces_ptr = []
    cc.FacesVertical(vertical_faces_ptr)
    assert len(vertical_faces_ptr) == 5
    for face in vertical_faces_ptr:
        assert face.IsVertical()

    horizontal_faces_ptr = []
    cc.FacesHorizontal(horizontal_faces_ptr)
    assert len(horizontal_faces_ptr) == 4
    for face in horizontal_faces_ptr:
        assert face.IsHorizontal()


def test_cells():
    centroid = cc.Centroid()
    assert centroid.X() == 5.0
    assert centroid.Y() == 5.0
    assert centroid.Z() == 5.0

    cells_ptr = []
    cc.Cells(None, cells_ptr)
    assert len(cells_ptr) == 2

    for cell in cells_ptr:
        centroid = cell.Centroid()
        assert centroid.Z() == 5.0
        volume = CellUtility.Volume(cell)
        assert volume == pytest.approx(500.0)
        assert cell.Elevation() == 0.0
        assert cell.Height() == 10.0

        vertical_faces_ptr = []
        cell.FacesVertical(vertical_faces_ptr)
        assert len(vertical_faces_ptr) == 3

        cell_adjacent = False
        nowt_adjacent = False
        horiz_1 = False
        horiz_2 = False
        face_internal = False
        face_world = False

        for face in vertical_faces_ptr:
            adjacent_cells_ptr = face.Cells_Cached(cc)
            if len(adjacent_cells_ptr) == 2:
                cell_adjacent = True
            elif len(adjacent_cells_ptr) == 1:
                nowt_adjacent = True

            horiz_faces_ptr = face.HorizontalFacesSideways(cc)
            if len(horiz_faces_ptr) == 1:
                horiz_1 = True
            elif len(horiz_faces_ptr) == 2:
                horiz_2 = True

            for horiz_face in horiz_faces_ptr:
                assert horiz_face.IsHorizontal()

            if face.IsInternal(cc):
                face_internal = True
            elif face.IsWorld(cc):
                face_world = True

        assert cell_adjacent
        assert nowt_adjacent
        assert horiz_1
        assert horiz_2
        assert face_internal
        assert face_world

        horizontal_faces_ptr = []
        cell.FacesHorizontal(horizontal_faces_ptr)
        assert len(horizontal_faces_ptr) == 2

        top_faces_ptr = []
        cell.FacesTop(top_faces_ptr)
        assert len(top_faces_ptr) == 1
        for face in top_faces_ptr:
            assert face.IsHorizontal()
            assert face.Elevation() == 10.0
            assert face.Height() == 0.0

        bottom_faces_ptr = []
        cell.FacesBottom(bottom_faces_ptr)
        assert len(bottom_faces_ptr) == 1
        for face in bottom_faces_ptr:
            assert face.IsHorizontal()
            assert face.Elevation() == 0.0
            assert face.Height() == 0.0


output = Topology.Analyze(cc)
