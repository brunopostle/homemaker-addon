#!/usr/bin/python3

import os
import sys
import pytest
import ifcopenshell.api.root

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_site_by_name,
    get_building_by_name,
    create_storeys,
    get_context_by_name,
)
from molior.style import Style

api = ifcopenshell.api


@pytest.fixture
def ifc_setup():
    """Fixture to set up the IFC file for testing."""
    ifc = molior.ifc.init(name="My Project")
    body_context = get_context_by_name(ifc, context_identifier="Body")
    style_object = Style()

    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site")
    building = get_building_by_name(ifc, site, "My Building")
    create_storeys(ifc, building, {0.0: 0})

    api.root.create_entity(
        ifc,
        ifc_class="IfcBuildingElementProxy",
        name="My Extrusion",
    )

    ifc.createIfcCartesianTransformationOperator2D(
        None,
        None,
        ifc.createIfcCartesianPoint([0.0, 0.0]),
        1.0,
    )

    ifc.write("_test.ifc")
    return ifc


def test_noop(ifc_setup):
    """Placeholder test that ensures the setup works."""
    assert ifc_setup is not None
