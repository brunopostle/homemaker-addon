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
def closed_repeat():
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

    # closed repeat
    # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": None,
                    "back_cell": None,
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
                    "back_cell": None,
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
                    "back_cell": None,
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
                    "back_cell": None,
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
        normals=normals.normals,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    repeat = molior_object.build_trace(
        stylename="fancy",
        condition="top-backward-up",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )

    return repeat


@pytest.fixture
def open_repeat():
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

    # open repeat
    trace = ugraph.graph()
    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": None,
                    "back_cell": None,
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
                    "back_cell": None,
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
                    "back_cell": None,
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
        normals=normals.normals,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    repeat = molior_object.build_trace(
        stylename="fancy",
        condition="top-backward-up",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )

    return repeat


def test_closed_repeat_properties(closed_repeat):
    assert len(closed_repeat) == 4
    assert closed_repeat[0].height == 0.05
    assert closed_repeat[0].level == 2
    assert closed_repeat[0].name == "eaves corona"
    assert closed_repeat[0].typename == "eaves_corona"
    assert closed_repeat[3].__dict__["class"] == "Repeat"


if __name__ == "__main__":
    pytest.main()
