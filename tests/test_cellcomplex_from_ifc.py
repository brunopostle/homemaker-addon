"""The CellComplex stashed in a building can be retrieved from the building."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.ifc import get_parent_building
from molior.rooms import document_to_faces_and_widgets


def build():
    """Two rooms 4m square side by side"""
    rooms = [
        {
            "vertices": [[x, 0], [x + 4, 0], [x + 4, 4], [x, 4]],
            "elevation": 0,
            "height": 3,
            "usage": usage,
        }
        for x, usage in [(0, "living"), (4, "kitchen")]
    ]
    faces, widgets = document_to_faces_and_widgets({"rooms": rooms})
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=widgets)
    molior_object.execute()
    return molior_object


def test_building_is_its_own_parent():
    molior_object = build()
    building = molior_object.file.by_type("IfcBuilding")[0]
    assert get_parent_building(building) == building
    space = molior_object.file.by_type("IfcSpace")[0]
    assert get_parent_building(space) == building
    site = molior_object.file.by_type("IfcSite")[0]
    assert get_parent_building(site) is None


def test_cellcomplex_from_building_or_space():
    molior_object = build()
    building = molior_object.file.by_type("IfcBuilding")[0]
    space = molior_object.file.by_type("IfcSpace")[0]
    for entity in (building, space):
        cellcomplex = Molior.get_cellcomplex_from_ifc(entity)
        assert cellcomplex is not None
        cells_ptr = []
        cellcomplex.Cells(None, cells_ptr)
        assert sorted(cell.Usage() for cell in cells_ptr) == ["kitchen", "living"]
