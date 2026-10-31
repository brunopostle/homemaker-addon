"""Doors in interior walls have to fit under a sloping ceiling."""

import os
import sys

import ifcopenshell.util.placement
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.rooms import document_to_faces_and_widgets


def lean_to(height_start, height_end, depth=6.0):
    """Two rooms either side of an interior wall at x=4, its top slopes in y"""
    z0, z1 = height_start, height_end
    vertices = [[[4, 0, 0], [4, depth, 0], [4, depth, z1], [4, 0, z0]]]
    for x0, x1 in ((0, 4), (4, 8)):
        vertices += [
            [[x0, 0, 0], [x1, 0, 0], [x1, depth, 0], [x0, depth, 0]],
            [[x0, 0, z0], [x1, 0, z0], [x1, depth, z1], [x0, depth, z1]],
            [[x0, 0, 0], [x1, 0, 0], [x1, 0, z0], [x0, 0, z0]],
            [[x0, depth, 0], [x1, depth, 0], [x1, depth, z1], [x0, depth, z1]],
        ]
    vertices += [[[x, 0, 0], [x, depth, 0], [x, depth, z1], [x, 0, z0]] for x in (0, 8)]
    faces, widgets = document_to_faces_and_widgets(
        {"faces": [{"vertices": item, "stylename": "default"} for item in vertices]}
    )
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=widgets)
    molior_object.execute()
    return [door_extent(door) for door in molior_object.file.by_type("IfcDoor")]


def door_extent(door):
    """Distance along the wall of each side of a door, and height of the top"""
    placement = ifcopenshell.util.placement.get_placement(door.ObjectPlacement)
    y, z = placement[1][3], placement[2][3]
    near, far = sorted([y, y + placement[1][0] * door.OverallWidth])
    return near, far, z + door.OverallHeight


@pytest.mark.parametrize(
    "height_start,height_end", [(1.0, 3.0), (1.9, 3.0), (3.0, 1.0)]
)
def test_door_fits_under_slope(height_start, height_end):
    doors = lean_to(height_start, height_end)
    assert len(doors) == 1
    near, far, top = doors[0]
    assert far - near == pytest.approx(0.8)
    slope = (height_end - height_start) / 6.0
    assert top <= height_start + slope * near + 0.001
    assert top <= height_start + slope * far + 0.001


def test_door_stays_where_it_fits():
    doors = lean_to(3.0, 1.0)
    assert doors[0][0] == pytest.approx(0.5)


def test_door_moves_no_further_than_it_needs():
    doors = lean_to(1.9, 3.0)
    # the roofline reaches the top of the door 1.2m along the wall
    assert 1.2 - 0.001 <= doors[0][0] <= 1.3


def test_door_is_removed_when_it_fits_nowhere():
    # tall enough for the door at its highest point, but too steep for its width
    assert lean_to(1.0, 2.4, depth=2.0) == []
