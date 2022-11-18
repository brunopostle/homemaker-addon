#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_site_by_name,
    get_building_by_name,
    create_storeys,
    get_context_by_name,
)
from molior.style import Style

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = molior.ifc.init(name="My Project")
        self.body_context = get_context_by_name(ifc, context_identifier="Body")
        self.style_object = Style()

        project = ifc.by_type("IfcProject")[0]
        site = get_site_by_name(ifc, project, "My Site")
        building = get_building_by_name(ifc, site, "My Building")
        create_storeys(ifc, building, {0.0: 0})

        element = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingElementProxy",
            name="My Extrusion",
        )
        directrix = [[-5.0, 1.0], [-1.0, 1.0], [-1.0, 5.0], [-5.0, 5.0], [-5.0, 1.0]]

        transform = ifc.createIfcCartesianTransformationOperator2D(
            None,
            None,
            ifc.createIfcCartesianPoint([0.0, 0.0]),
            1.0,
        )

        ifc.write("_test.ifc")

    def test_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
