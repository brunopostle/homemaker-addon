#!/usr/bin/python3

import sys
import os
import pytest

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist.fitness import p159_light_on_two_sides_of_every_room
from molior import Molior
import topologist.vertex

assert topologist.vertex


@pytest.fixture
def setup_building():
    widgets_text = []

    faces_text = [
        [
            [
                [-1.0, -1.0, -1.0],
                [1.0, -1.0, -1.0],
                [1.0, -1.0, 1.0],
                [-1.0, -1.0, 1.0],
            ],
            "framing",
        ],
        [
            [
                [-1.0, 1.0, -1.0],
                [1.0, 1.0, -1.0],
                [1.0, 1.0, 1.0],
                [-1.0, 1.0, 1.0],
            ],
            "framing",
        ],
        [
            [
                [-1.0, -1.0, -1.0],
                [1.0, -1.0, -1.0],
                [1.0, 1.0, -1.0],
                [-1.0, 1.0, -1.0],
            ],
            "framing",
        ],
        [
            [
                [-1.0, -1.0, 1.0],
                [1.0, -1.0, 1.0],
                [1.0, 1.0, 1.0],
                [-1.0, 1.0, 1.0],
            ],
            "framing",
        ],
        [
            [
                [-1.0, -1.0, -1.0],
                [-1.0, -1.0, 1.0],
                [-1.0, 1.0, 1.0],
                [-1.0, 1.0, -1.0],
            ],
            "framing",
        ],
        [
            [
                [1.0, -1.0, -1.0],
                [1.0, -1.0, 1.0],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, -1.0],
            ],
            "framing",
        ],
    ]

    widgets = []
    for widget in widgets_text:
        vertex = Vertex.ByCoordinates(*widget[1])
        vertex.Set("usage", widget[0])
        widgets.append(vertex)

    faces_ptr = []
    for face in faces_text:
        face_ptr = Face.ByVertices([Vertex.ByCoordinates(*v) for v in face[0]])
        face_ptr.Set("stylename", face[1])
        faces_ptr.append(face_ptr)

    # Generate a Topologic CellComplex
    cc = CellComplex.ByFaces(faces_ptr, 0.0001)
    # Give every Cell and Face an index number
    cc.IndexTopology()
    # Copy styles from Faces to the CellComplex
    cc.ApplyDictionary(faces_ptr)
    # Assign Cell usages from widgets
    cc.AllocateCells(widgets)
    # Generate a circulation Graph
    circulation = cc.Adjacency()
    circulation.Circulation(cc)
    shortest_path_table = circulation.ShortestPathTable()
    circulation.Separation(shortest_path_table, cc)

    return {
        "cc": cc,
        "circulation": circulation,
        "shortest_path_table": shortest_path_table,
    }


def test_circulation(setup_building):
    cc = setup_building["cc"]
    circulation = setup_building["circulation"]
    shortest_path_table = setup_building["shortest_path_table"]

    cells_ptr = []
    cc.Cells(None, cells_ptr)
    assert circulation.IsConnected()

    assessor = p159_light_on_two_sides_of_every_room.Assessor(
        cc, circulation, shortest_path_table
    )
    for cell in cells_ptr:
        assessor.execute(cell)


def test_molior(setup_building):
    cc = setup_building["cc"]
    circulation = setup_building["circulation"]

    traces, normals, elevations = cc.GetTraces()
    hulls = cc.GetHulls()

    molior_object = Molior(
        circulation=circulation,
        traces=traces,
        hulls=hulls,
        normals=normals,
        cellcomplex=cc,
        name="My test building",
        elevations=elevations,
    )
    molior_object.execute()
    molior_object.file.write("_test.ifc")

    assert len(molior_object.file.by_type("IfcWindow")) == 4
    assert len(molior_object.file.by_type("IfcWall")) == 4
    assert molior_object.file.by_type("IfcWall")[0].Name == "exterior-empty"


if __name__ == "__main__":
    pytest.main()
