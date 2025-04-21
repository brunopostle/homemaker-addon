#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
import topologist.normals
from molior import Molior
import molior.ifc


@pytest.fixture
def setup_wall():
    trace = ugraph.graph()
    normals = topologist.normals.Normals()
    vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
    vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
    vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
    coor_0 = vertex_0.CoorAsString()
    coor_1 = vertex_1.CoorAsString()
    coor_2 = vertex_2.CoorAsString()
    vertex_3 = Vertex.ByCoordinates(1.0, 0.0, 5.15)
    vertex_4 = Vertex.ByCoordinates(5.0, 0.0, 6.15)
    vertex_5 = Vertex.ByCoordinates(8.0, 4.0, 6.15)

    dummy_cell = Vertex.ByCoordinates(0.0, 0.0, 0.0)

    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": Face.ByVertices([vertex_1, vertex_2, vertex_5, vertex_4]),
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
                    "face": Face.ByVertices([vertex_0, vertex_1, vertex_4, vertex_3]),
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    paths = trace.find_paths()

    ifc = molior.ifc.init(name="My Project")

    molior_object = Molior(
        file=ifc,
        circulation=None,
        normals=normals.normals,
        cellcomplex=dummy_cell,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    wall = molior_object.build_trace(
        stylename="default",
        condition="external",
        elevation=3.15,
        height=2.85,
        chain=paths[0],
    )[0]

    return {"wall": wall, "ifc": ifc}


def test_sanity(setup_wall):
    wall = setup_wall["wall"]
    assert wall.length_segment(0) == 4
    assert wall.length_segment(1) == 5
    assert wall.height == 2.85
    assert wall.level == 2
    assert wall.name == "exterior"
    assert wall.__dict__["class"] == "Wall"


def test_query(setup_wall):
    wall = setup_wall["wall"]
    assert pytest.approx(wall.length_openings(0)) == 3.22
    assert pytest.approx(wall.length_openings(1)) == 3.22
    assert pytest.approx(wall.border(0)[0]) == 0.08
    assert pytest.approx(wall.border(0)[1]) == 0.08
    assert pytest.approx(wall.border(1)[0]) == 0.08
    assert pytest.approx(wall.border(1)[1]) == 0.08


def test_align_openings(setup_wall):
    wall = setup_wall["wall"]
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.545
    wall.align_openings(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.545
    assert pytest.approx(wall.openings[1][0]["along"]) == 0.795
    wall.align_openings(1)
    assert pytest.approx(wall.openings[1][0]["along"]) == 0.795


def test_fix_overlaps(setup_wall):
    wall = setup_wall["wall"]
    assert len(wall.openings[0]) == 2
    wall.fix_overlaps(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.545

    wall.openings[0].append({"family": "toilet outside door", "along": 2.5, "size": 0})
    wall.openings[0].append({"family": "toilet outside door", "along": 0.5, "size": 0})
    assert wall.openings[0][1]["along"] == 2.545
    assert wall.openings[0][2]["along"] == 2.5

    wall.fix_overlaps(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.545
    assert wall.openings[0][1]["along"] == 2.545
    assert pytest.approx(wall.openings[0][2]["along"]) == 4.255

    wall.fix_overrun(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == -1.89
    assert pytest.approx(wall.openings[0][1]["along"]) == 0.11
    assert pytest.approx(wall.openings[0][2]["along"]) == 1.82

    wall.fix_underrun(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == -1.6

    wall.align_openings(0)
    assert wall.openings[0][1]["along"] == 1.045


def test_fix_segment(setup_wall):
    wall = setup_wall["wall"]
    wall.fix_segment(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.545

    wall.fix_segment(1)
    assert pytest.approx(wall.openings[1][0]["along"]) == 0.795
    assert wall.openings[1][1]["along"] == 3.295


def test_fix_heights(setup_wall):
    wall = setup_wall["wall"]
    assert wall.openings[0][0]["size"] == 6
    wall.fix_heights(0)
    assert wall.openings[0][0]["size"] == 3


def test_write(setup_wall):
    ifc = setup_wall["ifc"]
    ifc.write("_test.ifc")
    # Since this is primarily testing file writing functionality,
    # we just assert that the code runs without errors
    assert True


if __name__ == "__main__":
    pytest.main(["-v"])
