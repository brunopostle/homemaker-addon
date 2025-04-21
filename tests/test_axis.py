import pytest
from topologic_core import Vertex, Edge, Wire, Face, CellComplex

import topologist.face

assert topologist.face


@pytest.fixture
def cell_complex():
    """Fixture to create a simple cube CellComplex for testing"""
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

    # faces have mixed normals
    faces_by_vertex_id = [
        [0, 1, 2, 3],
        [5, 6, 2, 1],
        [6, 7, 3, 2],
        [0, 4, 7, 3],
        [0, 1, 5, 4],
        [4, 5, 6, 7],
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
    vertical_faces_ptr = []
    cell_complex.FacesVertical(vertical_faces_ptr)
    assert len(vertical_faces_ptr) == 4

    outer_edges_ptr = []
    outer_top_edges_ptr = []

    # four vertical outer faces
    for face in vertical_faces_ptr:
        assert face.IsVertical()

        # faces face out, so axis_outer and axis_outer_top should be anticlockwise
        axis_outer = face.AxisOuter()
        axis_outer_top = face.AxisOuterTop()

        outer_edges_ptr.append(
            Edge.ByStartVertexEndVertex(axis_outer[0], axis_outer[1])
        )
        outer_top_edges_ptr.append(
            Edge.ByStartVertexEndVertex(axis_outer_top[0], axis_outer_top[1])
        )

    # construct four sided wires for top and bottom
    wire_axis = Wire.ByEdges(outer_edges_ptr)
    wire_axis_top = Wire.ByEdges(outer_top_edges_ptr)

    axis_vertices_ptr = []
    axis_top_vertices_ptr = []

    wire_axis.Vertices(None, axis_vertices_ptr)
    wire_axis_top.Vertices(None, axis_top_vertices_ptr)

    assert len(axis_vertices_ptr) == 4
    assert len(axis_top_vertices_ptr) == 4

    face_axis = Face.ByVertices(axis_vertices_ptr)
    face_axis_top = Face.ByVertices(axis_top_vertices_ptr)

    # this should work ??!?
    # face_axis = Face.ByWire(wire_axis)
    # face_axis_top = Face.ByWire(wire_axis_top)

    normal = face_axis.Normal()
    normal_top = face_axis_top.Normal()

    # both faces are anticlockwise (normal up)
    assert normal[2] == 1.0
    assert normal_top[2] == 1.0
