"""Faces that don't make a CellComplex still make building elements."""

import collections
import os
import sys

import ifcopenshell.util.placement
import pytest
from topologic_core import Face, Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.rooms import document_to_faces_and_widgets


def room(x0, y0, x1, y1, elevation=0.0):
    return {
        "vertices": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
        "elevation": elevation,
        "height": 3.0,
        "usage": "living",
    }


def room_faces(*rooms):
    return document_to_faces_and_widgets({"rooms": list(rooms)})[0]


def face(vertices, stylename="default"):
    result = Face.ByVertices([Vertex.ByCoordinates(*vertex) for vertex in vertices])
    result.Set("stylename", stylename)
    return result


WALL = [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]
RETURN_WALL = [[4, 0, 0], [4, 4, 0], [4, 4, 3], [4, 0, 3]]


def build(faces):
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    assert molior_object.cellcomplex is None
    molior_object.execute()
    return molior_object


def count(molior_object):
    return collections.Counter(
        item.is_a() for item in molior_object.file.by_type("IfcElement")
    )


@pytest.mark.parametrize(
    "faces,walls,roofs",
    [
        (lambda: [face(WALL)], 1, 0),
        (lambda: [face(WALL), face(RETURN_WALL)], 2, 0),
        (lambda: room_faces(room(0, 0, 4, 4))[:-1], 3, 1),
        (lambda: room_faces(room(0, 0, 4, 4), room(10, 0, 14, 4)), 8, 2),
        (lambda: room_faces(room(0, 0, 4, 4), room(4, 4, 8, 8)), 8, 2),
        (lambda: room_faces(room(0, 0, 4, 4), room(4, 0, 8, 4, 3.0)), 8, 2),
    ],
    ids=["wall", "two walls", "open box", "apart", "corner", "edge"],
)
def test_faces_make_elements(faces, walls, roofs):
    molior_object = build(faces())
    elements = count(molior_object)
    exterior = [
        item
        for item in molior_object.file.by_type("IfcWall")
        if item.Name == "exterior"
    ]
    assert len(exterior) == walls
    assert elements["IfcRoof"] == roofs
    assert len(molior_object.file.by_type("IfcSpace")) == 0


def test_two_walls_at_a_corner_are_one_path():
    molior_object = build([face(WALL), face(RETURN_WALL)])
    chains = molior_object.traces["external"][0.0][3.0]["default"]
    assert [len(chain.edges()) for chain in chains] == [2]


def test_faces_keep_their_style():
    # walls in the 'arcade' style have a covering and no windows
    elements = count(build([face(WALL, "arcade")]))
    assert elements["IfcCovering"] == 1
    assert elements["IfcWindow"] == 0


def conditions(molior_object, condition, elevation):
    chains = molior_object.traces[condition][elevation][0.0]["default"]
    return sum(len(chain.edges()) for chain in chains)


@pytest.mark.parametrize("clockwise", [False, True], ids=["anticlockwise", "clockwise"])
def test_rooms_have_the_conditions_of_a_building(clockwise):
    rooms = [room(0, 0, 4, 4), room(10, 0, 14, 4)]
    if clockwise:
        rooms = [dict(item, vertices=item["vertices"][::-1]) for item in rooms]
    molior_object = build(room_faces(*rooms))
    assert conditions(molior_object, "bottom-backward-level", 0.0) == 8
    assert conditions(molior_object, "top-backward-level", 3.0) == 8
    assert not molior_object.traces.keys() & {
        "bottom-forward-level",
        "top-forward-level",
    }


def test_lite_mode_traces_match_a_cellcomplex():
    faces = room_faces(room(0, 0, 4, 4))
    building = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    faces = room_faces(room(0, 0, 4, 4), room(10, 0, 14, 4))
    lite = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    assert lite.cellcomplex is None
    expected = {"external", "bottom-backward-level", "top-backward-level"}
    assert expected <= building.traces.keys()
    assert set(lite.traces) == expected


def test_footing_and_walls_are_on_the_same_side_as_in_a_building():
    faces = room_faces(room(0, 0, 4, 4))
    building = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    building.execute()
    lite = build(room_faces(room(0, 0, 4, 4), room(10, 0, 14, 4)))

    def places(molior_object, ifc_class):
        result = set()
        for item in molior_object.file.by_type(ifc_class):
            placement = ifcopenshell.util.placement.get_placement(item.ObjectPlacement)
            if placement[0][3] < 5.0:
                result.add((round(placement[0][3], 3), round(placement[1][3], 3)))
        return result

    assert places(lite, "IfcWall") == places(building, "IfcWall")
    assert places(lite, "IfcFooting") == places(building, "IfcFooting")
    assert places(lite, "IfcFooting")


def test_a_wall_with_nothing_above_or_below_has_no_conditions():
    molior_object = build([face(WALL)])
    assert list(molior_object.traces) == ["external"]


def test_no_faces_are_refused():
    with pytest.raises(ValueError, match="No geometry"):
        Molior.from_faces_and_widgets(faces=[], widgets=[])


def test_web_server_generates_lite_mode():
    pytest.importorskip("fastapi")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
    from server import _generate_ifc

    document = {"rooms": [room(0, 0, 4, 4), room(4, 4, 8, 8)]}
    assert b"IFCWALL" in _generate_ifc(document, "share")
