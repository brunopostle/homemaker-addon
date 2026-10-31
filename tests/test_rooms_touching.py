"""Rooms touching at a corner, so the paths of their walls cross at a point."""

import math
import os
import sys

import ifcopenshell.util.placement
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior, NOT_A_CELLCOMPLEX
from molior.rooms import document_to_faces_and_widgets
import topologist.ugraph as ugraph


class Cell:
    def IsSame(self, other):
        return self is other


def edge(start, end, cell=None):
    return {start: [end, {"back_cell": cell}]}


def paths(edges):
    multigraph = ugraph.multigraph()
    for item in edges:
        multigraph.add_edge(item)
    return multigraph.find_paths()


def test_multigraph_chain_and_cycle():
    result = paths(
        [
            edge("B", "C"),
            edge("A", "B"),
            edge("X", "Y"),
            edge("Y", "Z"),
            edge("Z", "X"),
        ]
    )
    assert sorted(path.starts() for path in result) == [["A", "B"], ["X", "Y", "Z"]]
    assert [path.is_simple_cycle() for path in result] == [False, True]


def test_multigraph_paths_follow_the_cell_through_a_crossing():
    a = Cell()
    b = Cell()
    result = paths(
        [
            edge("P", "A2", a),
            edge("P", "B2", b),
            edge("A1", "P", a),
            edge("B1", "P", b),
        ]
    )
    assert sorted(path.edges() for path in result) == [
        [["A1", "P"], ["P", "A2"]],
        [["B1", "P"], ["P", "B2"]],
    ]


def test_multigraph_paths_end_at_a_crossing_without_a_shared_cell():
    result = paths(
        [
            edge("P", "A2", Cell()),
            edge("P", "B2", Cell()),
            edge("A1", "P", Cell()),
            edge("B1", "P", None),
        ]
    )
    assert len(result) == 4
    assert sum(len(path.edges()) for path in result) == 4


def test_multigraph_path_visiting_a_crossing_twice_keeps_every_edge():
    a = Cell()
    b = Cell()
    result = paths(
        [
            edge("P", "Q", a),
            edge("Q", "P", b),
            edge("P", "R", b),
            edge("R", "P", a),
        ]
    )
    edges = [item for path in result for item in path.edges()]
    assert sorted(edges) == [["P", "Q"], ["P", "R"], ["Q", "P"], ["R", "P"]]


def room(x0, y0, x1, y1, usage, stylename="default"):
    return {
        "vertices": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        "elevation": 0.0,
        "height": 3.0,
        "usage": usage,
        "stylename": stylename,
    }


def build(rooms):
    faces, widgets = document_to_faces_and_widgets({"rooms": rooms})
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=widgets)
    molior_object.execute()
    return molior_object


def external_chains(molior_object):
    return molior_object.traces["external"][0.0][3.0]


def test_rooms_touching_at_a_corner_each_have_all_their_walls():
    molior_object = build(
        [
            room(0, 0, 4, 4, "living"),
            room(4, 4, 8, 8, "living"),
            room(4, 0, 8, 4, "outside"),
            room(0, 4, 4, 8, "outside"),
        ]
    )
    chains = external_chains(molior_object)["default"]
    assert [chain.is_simple_cycle() for chain in chains] == [True, True]
    assert [len(chain.edges()) for chain in chains] == [4, 4]

    walls = [
        wall
        for wall in molior_object.file.by_type("IfcWall")
        if wall.Name == "exterior"
    ]
    assert len(walls) == 8
    for wall in walls:
        placement = ifcopenshell.util.placement.get_placement(wall.ObjectPlacement)
        assert all(math.isfinite(value) for value in placement.flatten())


def test_rooms_touching_at_a_corner_in_different_styles():
    molior_object = build(
        [
            room(0, 0, 4, 4, "living"),
            room(4, 4, 8, 8, "living", "tuscan"),
            room(4, 0, 8, 4, "outside"),
            room(0, 4, 4, 8, "outside", "tuscan"),
        ]
    )
    chains = external_chains(molior_object)
    assert sum(len(chain.edges()) for chain in chains["default"]) == 4
    assert sum(len(chain.edges()) for chain in chains["tuscan"]) == 4


def test_ring_of_rooms_touching_itself_at_a_corner():
    rooms = [
        room(4 * x, 4 * y, 4 * x + 4, 4 * y + 4, "living")
        for x, y in [(1, 1), (0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (2, 2)]
    ]
    rooms += [room(8, 4, 12, 8, "outside"), room(4, 8, 8, 12, "outside")]
    chains = external_chains(build(rooms))["default"]
    edges = [item for chain in chains for item in chain.edges()]
    assert len(edges) == len(set(tuple(item) for item in edges))
    # three faces each for the two rooms at the corner, two each for the others
    assert len(edges) == 16


NOT_BUILDINGS = {
    "touching at a corner": [room(0, 0, 4, 4, "living"), room(4, 4, 8, 8, "living")],
    "apart": [room(0, 0, 4, 4, "living"), room(10, 0, 14, 4, "living")],
}


@pytest.mark.parametrize("rooms", NOT_BUILDINGS.values(), ids=NOT_BUILDINGS.keys())
def test_rooms_that_do_not_make_a_building_are_refused(rooms):
    faces, widgets = document_to_faces_and_widgets({"rooms": rooms})
    with pytest.raises(ValueError, match="do not make a building"):
        Molior.from_faces_and_widgets(faces=faces, widgets=widgets)


def test_faces_that_do_not_enclose_a_room_are_refused():
    faces, widgets = document_to_faces_and_widgets(
        {"rooms": [room(0, 0, 4, 4, "living")]}
    )
    with pytest.raises(ValueError, match="do not make a building"):
        Molior.from_faces_and_widgets(faces=faces[:-1], widgets=widgets)


def test_no_faces_are_refused():
    with pytest.raises(ValueError, match="do not make a building"):
        Molior.from_faces_and_widgets(faces=[], widgets=[])


def test_web_server_reports_rooms_that_do_not_make_a_building():
    pytest.importorskip("fastapi")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
    from server import _generate_ifc, _validate_geometry

    document = {"rooms": NOT_BUILDINGS["touching at a corner"]}
    assert _validate_geometry(document, "share") == {
        "valid": False,
        "error": NOT_A_CELLCOMPLEX,
    }
    with pytest.raises(ValueError, match="do not make a building"):
        _generate_ifc(document, "share")
    good = {"rooms": [room(0, 0, 4, 4, "living")]}
    assert _validate_geometry(good, "share")["valid"] is True
