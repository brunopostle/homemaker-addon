import pytest
import os
import sys

from topologic_core import (
    Vertex,
    Face,
    CellComplex,
    CellUtility,
    Graph,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.helpers import string_to_coor


@pytest.fixture
def create_cell_complex():
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
    return cc


def test_faces_cc(create_cell_complex):
    cc = create_cell_complex
    all_faces_ptr = []
    cc.Faces(None, all_faces_ptr)
    assert len(all_faces_ptr) == 14
    for face in all_faces_ptr:
        cells_ptr = face.Cells_Cached(cc)
        assert len(cells_ptr) > 0
        assert len(cells_ptr) < 3

    vertical_faces_ptr = []
    cc.FacesVertical(vertical_faces_ptr)
    assert len(vertical_faces_ptr) == 9
    for face in vertical_faces_ptr:
        assert face.IsVertical()

    horizontal_faces_ptr = []
    cc.FacesHorizontal(horizontal_faces_ptr)
    assert len(horizontal_faces_ptr) == 5
    for face in horizontal_faces_ptr:
        assert face.IsHorizontal()


def test_cells(create_cell_complex):
    cc = create_cell_complex
    centroid = cc.Centroid()
    assert centroid.X() == 5.0
    assert centroid.Y() == 5.0
    assert centroid.Z() == 10.0

    cells_ptr = []
    cc.Cells(None, cells_ptr)
    assert len(cells_ptr) == 3

    for cell in cells_ptr:
        centroid = cell.Centroid()
        volume = CellUtility.Volume(cell)
        planarea = cell.PlanArea()
        externalwallarea = cell.ExternalWallArea(cc)
        crinkliness = cell.Crinkliness(cc)

        vertical_faces_ptr = []
        cell.FacesVertical(vertical_faces_ptr)

        horizontal_faces_ptr = []
        cell.FacesHorizontal(horizontal_faces_ptr)

        above_cells_ptr = []
        cell.CellsAbove(cc, above_cells_ptr)
        if len(above_cells_ptr) == 1:
            assert volume == pytest.approx(500.0)
            assert planarea == pytest.approx(50.0)
            assert externalwallarea == pytest.approx(200.0)
            assert crinkliness == pytest.approx(4.0)
            cell.Set("usage", "Kitchen")
        elif len(above_cells_ptr) == 0:
            assert volume == pytest.approx(1000.0)
            assert planarea == pytest.approx(100.0)
            assert externalwallarea == pytest.approx(400.0)
            assert crinkliness == pytest.approx(4.0)
            cell.Set("usage", "Bedroom")

            vertical_faces_ptr = []
            cell.FacesVertical(vertical_faces_ptr)

            for face in vertical_faces_ptr:
                top_edges_ptr = []
                bottom_edges_ptr = []

                face.EdgesTop(top_edges_ptr)
                face.EdgesBottom(bottom_edges_ptr)
                assert len(top_edges_ptr) == 1
                assert len(bottom_edges_ptr) == 1

                assert not face.FaceAbove(cc)
                assert face.FacesBelow(cc)

        below_cells_ptr = []
        cell.CellsBelow(cc, below_cells_ptr)
        if len(below_cells_ptr) == 2:
            assert volume == pytest.approx(1000.0)
            assert cell.Usage() == "Bedroom"
        elif len(below_cells_ptr) == 0:
            assert volume == pytest.approx(500.0)
            assert cell.Usage() == "Kitchen"

    cells_ptr = []
    cc.Cells(None, cells_ptr)
    has_kitchen = False
    has_bedroom = False
    for cell in cells_ptr:
        if cell.Usage() == "Bedroom":
            has_bedroom = True
        if cell.Usage() == "Kitchen":
            has_kitchen = True
    assert has_bedroom
    assert has_kitchen


def test_faces(create_cell_complex):
    cc = create_cell_complex
    vertical_faces_ptr = []
    cc.FacesVertical(vertical_faces_ptr)
    assert len(vertical_faces_ptr) == 9

    horizontal_faces_ptr = []
    cc.FacesHorizontal(horizontal_faces_ptr)
    assert len(horizontal_faces_ptr) == 5


def test_graph(create_cell_complex):
    cc = create_cell_complex
    traces, normals, elevations = cc.GetTraces()
    traces_external = traces["external"]
    assert len(traces_external) == 2
    assert len(traces_external[0.0]) == 1
    assert len(traces_external[10.0]) == 1

    lower = traces_external[0.0][10.0]["default"]
    assert len(lower) == 1
    assert len(lower[0].nodes()) == 4
    assert len(lower[0].edges()) == 4
    cycle = lower[0]
    assert cycle.is_simple_cycle()
    for node in cycle.nodes():
        assert string_to_coor(node)[2] == 0.0

    data = cycle.get_edge_data(["0.0__10.0__0.0", "0.0__0.0__0.0"])
    assert len(data) == 5
    assert data["front_cell"] is None

    faces_ptr = data["start_vertex"].Faces_Cached(cc)
    assert len(faces_ptr) == 3

    faces_ptr = []
    data["face"].AdjacentFaces(cc, faces_ptr)
    assert len(faces_ptr) == 6

    upper = traces_external[10.0][10.0]["default"]
    assert len(upper[0].nodes()) == 4
    assert len(upper[0].edges()) == 4

    nodes = upper[0].nodes()
    for node in nodes:
        assert string_to_coor(node)[2] == 10.0
        assert len(string_to_coor(node)[0:2]) == 2

    traces_internal = traces["internal"][0.0][10.0]["default"]
    for graph in traces_internal:
        assert len(graph.nodes()) == 2
        assert len(graph.edges()) == 1

        for edge in graph.edges():
            data = graph.get_edge_data(edge)
            start = data["start_vertex"]
            end = data["end_vertex"]
            face = data["face"]

            assert start.X() == 10.0
            assert start.Y() == 10.0
            assert start.Z() == 0.0
            assert end.X() == 0.0
            assert end.Y() == 0.0
            assert end.Z() == 0.0

            centroid = face.Centroid()
            assert centroid.X() == 5.0
            assert centroid.Y() == 5.0
            assert centroid.Z() == 5.0
            assert face.Type() == 8


def test_elevations(create_cell_complex):
    cc = create_cell_complex
    traces, normals, elevations = cc.GetTraces()
    assert len(elevations) == 3
    assert elevations[0.0] == 0
    assert elevations[10.0] == 1
    assert elevations[20.0] == 2


def test_connectivity(create_cell_complex):
    cc = create_cell_complex
    graph = Graph.ByTopology(cc, True, False, False, False, False, False, 0.0001)
    topology = graph.Topology()
    edges_ptr = []
    topology.Edges(None, edges_ptr)
    assert len(edges_ptr) == 3
