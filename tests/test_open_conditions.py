"""Traces where walls meet 'outside' Cells: footings, and open faces above or below."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.rooms import document_to_faces_and_widgets


def room(y0, y1, elevation, usage):
    return {
        "vertices": [[0, y0], [4, y0], [4, y1], [0, y1]],
        "elevation": elevation,
        "height": 3.0,
        "usage": usage,
    }


def build(rooms):
    faces, widgets = document_to_faces_and_widgets({"rooms": rooms})
    return Molior.from_faces_and_widgets(faces=faces, widgets=widgets)


def edges(molior_object, condition, elevation):
    """Each edge of a trace as a sorted pair of 2D coordinates"""
    result = set()
    for chains in molior_object.traces[condition][elevation][0.0].values():
        for chain in chains:
            for edge in chain.edges():
                result.add(
                    tuple(
                        sorted(
                            tuple(float(c) for c in node.split("__")[:2])
                            for node in edge[:2]
                        )
                    )
                )
    return result


def test_wall_facing_outside_cell_has_a_footing():
    molior_object = build([room(0, 4, 0.0, "living"), room(4, 6, 0.0, "outside")])
    assert edges(molior_object, "internal-footing", 0.0) == {((0.0, 4.0), (4.0, 4.0))}

    molior_object.execute()
    footings = [
        item
        for item in molior_object.file.by_type("IfcFooting")
        if item.Name == "internal ground beam"
    ]
    assert len(footings) == 1


def test_wall_between_two_outside_cells_has_no_footing():
    molior_object = build([room(0, 4, 0.0, "outside"), room(4, 6, 0.0, "outside")])
    assert "internal-footing" not in molior_object.traces


def test_wall_facing_outside_cell_above_a_room_has_a_beam():
    molior_object = build(
        [
            room(0, 6, 0.0, "living"),
            room(0, 4, 3.0, "bedroom"),
            room(4, 6, 3.0, "outside"),
        ]
    )
    assert edges(molior_object, "internal-beam", 3.0) == {((0.0, 4.0), (4.0, 4.0))}
    assert "internal-footing" not in molior_object.traces


def test_top_of_wall_with_open_face_above():
    molior_object = build(
        [
            room(0, 6, 0.0, "living"),
            room(0, 4, 3.0, "bedroom"),
            room(4, 6, 3.0, "outside"),
        ]
    )
    assert edges(molior_object, "top-open", 3.0) == {
        ((0.0, 4.0), (0.0, 6.0)),
        ((0.0, 6.0), (4.0, 6.0)),
        ((4.0, 4.0), (4.0, 6.0)),
    }
    # the rest of the wall continues up
    assert edges(molior_object, "top-vertical-up", 3.0) == {
        ((0.0, 0.0), (0.0, 4.0)),
        ((0.0, 0.0), (4.0, 0.0)),
        ((4.0, 0.0), (4.0, 4.0)),
    }
    molior_object.execute()


def test_bottom_of_wall_with_open_face_below():
    molior_object = build(
        [
            room(0, 4, 0.0, "living"),
            room(4, 6, 0.0, "outside"),
            room(0, 6, 3.0, "bedroom"),
        ]
    )
    assert edges(molior_object, "bottom-open", 3.0) == {
        ((0.0, 4.0), (0.0, 6.0)),
        ((0.0, 6.0), (4.0, 6.0)),
        ((4.0, 4.0), (4.0, 6.0)),
    }
    assert edges(molior_object, "bottom-vertical-down", 3.0) == {
        ((0.0, 0.0), (0.0, 4.0)),
        ((0.0, 0.0), (4.0, 0.0)),
        ((4.0, 0.0), (4.0, 4.0)),
    }
    molior_object.execute()
