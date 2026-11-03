"""A room with no way in is reported, the building is still made."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
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


def test_room_cut_off_from_the_rest_is_reported():
    # a bedroom only gets a door to a stair or circulation
    molior_object = build_row(["living", "living", "bedroom"])
    components = molior_object.circulation.Components()
    assert [len(component) for component in components] == [2, 1]
    assert len(molior_object.warnings) == 1
    assert molior_object.warnings[0].startswith(
        "No door connects bedroom/" + components[1][0] + " to the rest"
    )
    assert len(molior_object.file.by_type("IfcSpace")) == 3


def test_connected_rooms_are_not_reported():
    molior_object = build_row(["living", "living", "living"])
    assert len(molior_object.circulation.Components()) == 1
    assert molior_object.warnings == []
