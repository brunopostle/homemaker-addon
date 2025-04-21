import pytest
import sys
import os

from topologic_core import Vertex, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
import topologist.vertex

assert topologist.vertex


@pytest.fixture
def setup_cellcomplex():
    widgets_text = [
        ["Living", [0.0, 0.0, 1.0]],
    ]

    faces_text = [
        [
            [
                [-1.0, -1.0, 0.0],
                [1.0, -1.0, 0.0],
                [1.0, 1.0, 0.0],
                [-1.0, 1.0, 0.0],
            ],
            "default",
        ],
        [
            [
                [-1.0, -1.0, 1.0],
                [1.0, -1.0, 1.0],
                [1.0, 1.0, 1.0],
                [-1.0, 1.0, 1.0],
            ],
            "default",
        ],
        [
            [
                [-1.0, -1.0, 0.0],
                [-1.0, -1.0, 1.0],
                [-1.0, 1.0, 1.0],
                [-1.0, 1.0, 0.0],
            ],
            "default",
        ],
        [
            [
                [1.0, -1.0, 0.0],
                [1.0, -1.0, 1.0],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, 0.0],
            ],
            "default",
        ],
        [
            [
                [-1.0, 1.0, 0.0],
                [-1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0],
                [1.0, 1.0, 0.0],
            ],
            "blank",
        ],
        [
            [
                [-1.0, -1.0, 0.0],
                [-1.0, -1.0, 1.0],
                [1.0, -1.0, 1.0],
                [1.0, -1.0, 0.0],
            ],
            "blank",
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

    return cc, circulation


def test_molior(setup_cellcomplex):
    cc, circulation = setup_cellcomplex

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
