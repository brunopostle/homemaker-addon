"""A door opens into the more private room, the Space it belongs to."""

import os
import sys

import numpy as np
import ifcopenshell.util.element
import ifcopenshell.util.placement

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.ifc import get_thickness
from molior.rooms import document_to_faces_and_widgets


def build_row(usages):
    """Rooms 4m square side by side in x"""
    rooms = [
        {
            "vertices": [[x, 0], [x + 4, 0], [x + 4, 4], [x, 4]],
            "elevation": 0,
            "height": 3,
            "usage": usage,
        }
        for x, usage in zip(range(0, 4 * len(usages), 4), usages)
    ]
    faces, widgets = document_to_faces_and_widgets({"rooms": rooms})
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=widgets)
    molior_object.execute()
    return molior_object


def swings_into(door):
    """x coordinate of a point the door leaf sweeps, and the door's Space"""
    matrix = ifcopenshell.util.placement.get_placement(door.ObjectPlacement)
    point = matrix[:3, 3] + 0.4 * matrix[:3, 0] + 0.5 * matrix[:3, 1]
    space = ifcopenshell.util.element.get_container(door)
    return point, space


def interior_doors(molior_object):
    return [
        door
        for door in molior_object.file.by_type("IfcDoor")
        if "FrontCellIndex"
        in ifcopenshell.util.element.get_psets(door)["EPset_Topology"]
    ]


def test_doors_open_into_the_more_private_room():
    # the wall faces run stair to circulation, then circulation to bedroom, so
    # one door has to be turned round
    for usages in (
        ["stair", "circulation", "bedroom"],
        ["bedroom", "circulation", "stair"],
    ):
        molior_object = build_row(usages)
        doors = interior_doors(molior_object)
        assert len(doors) == 2
        for door in doors:
            point, space = swings_into(door)
            # circulation is the least separated, nothing opens into it
            assert not space.Name.startswith("circulation")
            if space.Name.startswith(usages[0]):
                assert 0.0 < point[0] < 4.0
            else:
                assert 8.0 < point[0] < 12.0


def test_turned_door_stays_in_its_opening():
    molior_object = build_row(["stair", "circulation", "bedroom"])
    turned = 0
    for door in interior_doors(molior_object):
        opening = door.FillsVoids[0].RelatingOpeningElement
        wall = opening.VoidsElements[0].RelatingBuildingElement
        thickness = get_thickness(
            molior_object.file, ifcopenshell.util.element.get_type(wall)
        )
        matrix_door = ifcopenshell.util.placement.get_placement(door.ObjectPlacement)
        matrix = ifcopenshell.util.placement.get_placement(opening.ObjectPlacement)
        if np.allclose(matrix_door, matrix):
            continue
        # turned round about the far corner of the opening, on the other face
        turned += 1
        assert np.allclose(matrix_door[:3, 0], -matrix[:3, 0])
        assert np.allclose(matrix_door[:3, 1], -matrix[:3, 1])
        assert np.allclose(
            matrix_door[:3, 3],
            matrix[:3, 3]
            + door.OverallWidth * matrix[:3, 0]
            + thickness * matrix[:3, 1],
        )
    assert turned == 1
