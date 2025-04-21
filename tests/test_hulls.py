#!/usr/bin/python3

import os
import sys
import pytest

from topologic_core import (
    Vertex,
    Face,
    CellComplex,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
import molior.ifc


@pytest.fixture
def cell_complex():
    """Create a CellComplex for testing"""
    vertices = [
        Vertex.ByCoordinates(*point)
        for point in [
            [0.0, 0.0, 0.0],
            [10.0, 2.0, 0.0],
            [10.0, 12.0, 0.0],
            [0.0, 10.0, 0.0],
            [0.0, 0.0, 10.0],
            [10.0, 2.0, 10.0],
            [10.0, 12.0, 10.0],
            [0.0, 10.0, 10.0],
            [0.0, 5.0, 15.0],
            [10.0, 7.0, 15.0],
        ]
    ]

    faces_by_vertex_id = [
        [0, 1, 2, 3],
        [0, 1, 5, 4],
        [2, 3, 7, 6],
        [1, 2, 6, 9, 5],
        [0, 4, 8, 7, 3],
        [4, 5, 9, 8],
        [9, 8, 7, 6],
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
    return CellComplex.ByFaces(faces_ptr, 0.0001)


def test_faces_cc(cell_complex):
    """Test faces of the CellComplex"""
    all_faces_ptr = []
    cell_complex.Faces(None, all_faces_ptr)
    assert len(all_faces_ptr) == 7

    # Count upward faces
    count = sum(1 for face in all_faces_ptr if face.IsUpward())
    assert count == 2

    # Test vertical faces
    vertical_faces_ptr = []
    cell_complex.FacesVertical(vertical_faces_ptr)
    assert len(vertical_faces_ptr) == 4

    # Test horizontal faces
    horizontal_faces_ptr = []
    cell_complex.FacesHorizontal(horizontal_faces_ptr)
    assert len(horizontal_faces_ptr) == 1

    # Test inclined faces
    inclined_faces_ptr = []
    cell_complex.FacesInclined(inclined_faces_ptr)
    assert len(inclined_faces_ptr) == 2


def test_cells(cell_complex):
    """Test cells of the CellComplex"""
    centroid = cell_complex.Centroid()
    assert centroid.X() == 5.0
    assert centroid.Y() == 6.0
    assert centroid.Z() == 7.0  # average of vertex positions

    cells_ptr = []
    cell_complex.Cells(None, cells_ptr)
    assert len(cells_ptr) == 1


def test_traces(cell_complex):
    """Test traces and hulls of the CellComplex"""
    traces, normals, elevations = cell_complex.GetTraces()
    hulls = cell_complex.GetHulls()

    traces_external = traces["external"]
    assert len(traces_external) == 1
    assert len(traces_external[0.0]) == 2
    assert len(traces_external[0.0][10.0]) == 1
    assert len(traces_external[0.0][15.0]) == 1
    assert len(traces_external[0.0][10.0]["default"]) == 2
    assert len(traces_external[0.0][15.0]["default"]) == 2

    hulls_roof = hulls["roof"]
    assert len(hulls_roof) == 1
    assert len(hulls_roof["default"]) == 1

    assert len(hulls_roof["default"][0].nodes_all()) == 6
    assert len(hulls_roof["default"][0].faces_all()) == 2

    assert len(normals["top"].keys()) == 4
    assert len(normals["bottom"].keys()) == 4


def test_ifc(cell_complex, tmp_path):
    """Test IFC export"""
    traces, normals, elevations = cell_complex.GetTraces()
    hulls = cell_complex.GetHulls()

    ifc = molior.ifc.init(name="My Project")
    molior_object = Molior(
        file=ifc,
        circulation=None,
        traces=traces,
        hulls=hulls,
        name="My House",
        elevations=elevations,
        normals=normals,
        cellcomplex=cell_complex,
    )
    molior_object.execute()

    # Use tmp_path for creating a temporary file
    output_file = tmp_path / "_test.ifc"
    ifc.write(str(output_file))

    # Verify the file was created
    assert output_file.exists()
