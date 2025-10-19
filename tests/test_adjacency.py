import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologic_core import Vertex, Face, Cell, CellComplex

import topologist.face

assert topologist.face


@pytest.fixture
def cell_complex():
    """Fixture to create a cell complex for testing"""
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
    cc = CellComplex.ByFaces(faces_ptr, 0.0001)
    cc.IndexTopology()
    return cc


def test_vertices(cell_complex):
    graph = cell_complex.Adjacency()

    vertices_ptr = []
    graph.Vertices(vertices_ptr)
    assert len(vertices_ptr) == 6

    for vertex in vertices_ptr:
        vertex_class = vertex.Get("class")
        assert vertex_class in [
            "Face",
            "Cell",
        ], f"Unexpected vertex class: {vertex_class}"

        if vertex_class in ["Face", "Cell"]:
            assert vertex.Get("index") is not None


def test_faces(cell_complex):
    graph = cell_complex.Adjacency()
    faces = graph.Faces(cell_complex)

    # only three of the fourteen faces are represented in the graph
    assert len(faces) == 3

    for face in faces:
        assert isinstance(face, Face)

        # this Face has to have a Vertex in the Graph, that represents a Face
        vertex = face.GraphVertex(graph)
        assert isinstance(vertex, Vertex)
        assert vertex.Get("class") == "Face"

        # it should be the same Face
        entity = graph.GetEntity(cell_complex, vertex)
        assert face.IsSame(entity)


def test_cells(cell_complex):
    graph = cell_complex.Adjacency()
    cells = graph.Cells(cell_complex)

    assert len(cells) == 3

    for cell in cells:
        assert isinstance(cell, Cell)


def test_graphvertex(cell_complex):
    graph = cell_complex.Adjacency()

    cells_ptr = []
    cell_complex.Cells(None, cells_ptr)
    assert len(cells_ptr) == 3

    for cell in cells_ptr:
        # vertex is the node in the Graph that corresponds to this Cell
        vertex = cell.GraphVertex(graph)

        # it should be a Vertex, representing a Cell
        assert isinstance(vertex, Vertex)
        assert vertex.Get("class") == "Cell"

        # the equivalent entity in the CellComplex, should be a Cell
        entity = graph.GetEntity(cell_complex, vertex)
        assert isinstance(entity, Cell)

        # it should be the same Cell we started with
        assert cell.IsSame(entity)


def test_graphvertex2(cell_complex):
    graph = cell_complex.Adjacency()

    faces_ptr = []
    cell_complex.Faces(None, faces_ptr)
    assert len(faces_ptr) == 14

    for face in faces_ptr:
        # vertex is the node in the Graph that corresponds to this Face
        vertex = face.GraphVertex(graph)

        # the Graph may not have a node for this Face (e.g. purged, external wall)
        if vertex is None:
            continue

        # it should be a Vertex, representing a Face
        assert isinstance(vertex, Vertex)
        assert vertex.Get("class") == "Face"

        # the equivalent entity in the CellComplex, should be a Face
        entity = graph.GetEntity(cell_complex, vertex)
        assert isinstance(entity, Face)

        # it should be the same Face we started with
        assert face.IsSame(entity)


def test_isconnected(cell_complex):
    graph = cell_complex.Adjacency()
    assert graph.IsConnected()


def test_circulation(cell_complex):
    graph = cell_complex.Adjacency()

    # 3 faces and 3 cells = 6 vertices
    vertices_ptr = []
    graph.Vertices(vertices_ptr)
    assert len(vertices_ptr) == 6

    edges_ptr = []
    graph.Edges(edges_ptr)
    assert len(edges_ptr) == 6

    graph.Circulation(cell_complex)

    # 2 horizontal faces removed = 4 vertices
    vertices_ptr = []
    graph.Vertices(vertices_ptr)
    assert len(vertices_ptr) == 4

    edges_ptr = []
    graph.Edges(edges_ptr)
    assert len(edges_ptr) == 2

    assert not graph.IsConnected()
    dot = graph.Dot(cell_complex)
    assert isinstance(dot, str)


def test_shortest_path(cell_complex):
    graph = cell_complex.Adjacency()
    table = graph.ShortestPathTable()

    assert table["0"]["2"] == table["2"]["0"]
    assert table["1"]["2"] == table["2"]["1"]
    assert table["1"]["0"] == table["0"]["1"]


def test_separation(cell_complex):
    graph = cell_complex.Adjacency()
    table = graph.ShortestPathTable()
    graph.Separation(table, cell_complex)

    vertices_ptr = []
    graph.Vertices(vertices_ptr)

    for vertex in vertices_ptr:
        if vertex.Get("class") == "Cell":
            assert float(vertex.Get("separation")) > 0.0
