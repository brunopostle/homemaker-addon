#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex, Face, Graph

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph
import topologist.normals
from molior import Molior
import molior.ifc


@pytest.fixture
def setup_wall():
    trace = topologist.ugraph.graph()
    normals = topologist.normals.Normals()
    vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
    vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
    vertex_2 = Vertex.ByCoordinates(5.0, 0.0, 6.00)
    vertex_3 = Vertex.ByCoordinates(1.0, 0.0, 6.00)
    coor_0 = vertex_0.CoorAsString()
    coor_1 = vertex_1.CoorAsString()

    dummy_cell = Vertex.ByCoordinates(0.0, 0.0, 0.0)

    face = Face.ByVertices([vertex_0, vertex_1, vertex_2, vertex_3])
    # a real wall would have a Face and one or two Cells
    trace.add_edge(
        {
            coor_0: [
                coor_1,
                {
                    "start_vertex": vertex_0,
                    "end_vertex": vertex_1,
                    "face": face,
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
        circulation=Graph,
        normals=normals.normals,
        cellcomplex=dummy_cell,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    wall = molior_object.build_trace(
        stylename="default",
        condition="internal",
        elevation=3.15,
        height=2.85,
        chain=paths[0],
    )[0]

    wall.populate_interior_openings(0, "living", "living", 0)
    wall.fix_heights(0)
    wall.fix_segment(0)

    return wall


def test_sanity(setup_wall):
    wall = setup_wall
    assert wall.length_segment(0) == 4
    assert wall.height == 2.85
    assert wall.level == 2
    assert wall.name == "interior"
    assert wall.__dict__["class"] == "Wall"


def test_query(setup_wall):
    wall = setup_wall
    assert wall.length_openings(0) == 1.0
    assert wall.border(0)[0] == 0.08
    assert wall.border(0)[1] == 0.08


def test_align_openings(setup_wall):
    wall = setup_wall
    assert wall.openings[0][0]["along"] == 0.5
    wall.align_openings(0)
    assert wall.openings[0][0]["along"] == 0.5


def test_fix_overlaps(setup_wall):
    wall = setup_wall
    assert len(wall.openings[0]) == 1
    wall.fix_overlaps(0)
    assert wall.openings[0][0]["along"] == 0.5

    wall.openings[0].append({"family": "toilet outside door", "along": 2.5, "size": 0})
    wall.openings[0].append({"family": "toilet outside door", "along": 0.5, "size": 0})
    assert wall.openings[0][1]["along"] == 2.5
    assert wall.openings[0][2]["along"] == 0.5

    wall.fix_overlaps(0)
    assert wall.openings[0][0]["along"] == 0.5
    assert wall.openings[0][1]["along"] == 2.5
    assert pytest.approx(wall.openings[0][2]["along"]) == 3.6

    wall.fix_overrun(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == -0.18
    assert pytest.approx(wall.openings[0][1]["along"]) == 1.82
    assert pytest.approx(wall.openings[0][2]["along"]) == 2.92

    wall.fix_underrun(0)
    assert pytest.approx(wall.openings[0][0]["along"]) == 0.18

    wall.align_openings(0)
    assert pytest.approx(wall.openings[0][1]["along"]) == 1.82


def test_fix_segment(setup_wall):
    wall = setup_wall
    wall.fix_segment(0)
    assert wall.openings[0][0]["along"] == 0.5


def test_fix_heights(setup_wall):
    wall = setup_wall
    assert wall.openings[0][0]["size"] == 0
    wall.fix_heights(0)
    assert wall.openings[0][0]["size"] == 0


if __name__ == "__main__":
    pytest.main(["-v"])
