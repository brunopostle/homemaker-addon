#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
import topologist.normals
from molior import Molior
import molior.ifc


@pytest.fixture
def test_setup():
    trace = ugraph.graph()
    normals = topologist.normals.Normals()
    vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
    vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
    vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
    vertex_3 = Vertex.ByCoordinates(1.0, 4.0, 3.15)
    coor_0 = vertex_0.CoorAsString()
    coor_1 = vertex_1.CoorAsString()
    coor_2 = vertex_2.CoorAsString()
    coor_3 = vertex_3.CoorAsString()

    dummy_cell = Vertex.ByCoordinates(0.0, 0.0, 0.0)

    # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": None,
                    "back_cell": dummy_cell,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_0: [
                coor_1,
                {
                    "start_vertex": vertex_0,
                    "end_vertex": vertex_1,
                    "face": None,
                    "back_cell": dummy_cell,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_2: [
                coor_3,
                {
                    "start_vertex": vertex_2,
                    "end_vertex": vertex_3,
                    "face": None,
                    "back_cell": dummy_cell,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_3: [
                coor_0,
                {
                    "start_vertex": vertex_3,
                    "end_vertex": vertex_0,
                    "face": None,
                    "back_cell": dummy_cell,
                    "front_cell": None,
                },
            ]
        }
    )
    paths = trace.find_paths()

    ifc = molior.ifc.init(name="Our Project")

    molior_object = Molior(
        file=ifc,
        circulation=None,
        name="Our House",
        elevations={3.15: 2, 6.15: 3},
        normals=normals.normals,
        cellcomplex=dummy_cell,
    )
    molior_object.init_building()
    space = molior_object.build_trace(
        stylename="default",
        condition="kitchen",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )

    space2 = molior_object.build_trace(
        stylename="default",
        condition="kitchen",
        elevation=6.15,
        height=0.05,
        chain=paths[0],
    )

    stair = molior_object.build_trace(
        stylename="default",
        condition="stair",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )
    ifc.write("_test.ifc")

    return {"space": space, "space2": space2, "stair": stair}


def test_space_properties(test_setup):
    space = test_setup["space"]
    assert space[0].height == 0.05
    assert space[0].level == 2
    assert space[0].name == "kitchen-space"
    assert space[0].__dict__["class"] == "Space"


def test_floor_properties(test_setup):
    space = test_setup["space"]
    assert space[1].height == 0.05
    assert space[1].level == 2
    assert space[1].name == "kitchen-floor"
    assert space[1].__dict__["class"] == "Floor"


def test_stair_properties(test_setup):
    stair = test_setup["stair"]
    assert stair[2].height == 0.05
    assert stair[2].level == 2
    assert stair[2].name == "stair"
    assert stair[2].__dict__["class"] == "Stair"


if __name__ == "__main__":
    pytest.main()
