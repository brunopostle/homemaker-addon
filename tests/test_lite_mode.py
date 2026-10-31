"""Faces that don't make a CellComplex still make building elements."""

import collections
import os
import sys

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
    assert elements["IfcWall"] == walls
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


def test_no_faces_are_refused():
    with pytest.raises(ValueError, match="No geometry"):
        Molior.from_faces_and_widgets(faces=[], widgets=[])


def test_web_server_generates_lite_mode():
    pytest.importorskip("fastapi")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web"))
    from server import _generate_ifc

    document = {"rooms": [room(0, 0, 4, 4), room(4, 4, 8, 8)]}
    assert b"IFCWALL" in _generate_ifc(document, "share")
