#!/usr/bin/python3

import os
import sys
import numpy
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_site_by_name,
    get_building_by_name,
    create_storeys,
    assign_storey_byindex,
    assign_extrusion_fromDXF,
    get_context_by_name,
)
from molior.style import Style
from molior.geometry import matrix_align

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

        assign_extrusion_fromDXF(
            ifc,
            style_object=self.style_object,
            context_identifier="Body",
            element=element,
            directrix=directrix,
            stylename="courtyard",
            path_dxf="molior/style/share/courtyard/eaves_corona.dxf",
            transform=transform,
        )

        run("geometry.edit_object_placement", ifc, product=element, matrix=numpy.eye(4))
        assign_storey_byindex(ifc, element, building, 0)

        # do it again, hopefully dxf isn't reloaded

        element = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingElementProxy",
            name="Another Extrusion",
        )
        directrix = [[-5.0, 2.0], [-1.0, 2.0], [-1.0, 5.0], [-5.0, 5.0], [-5.0, 2.0]]

        assign_extrusion_fromDXF(
            ifc,
            style_object=self.style_object,
            context_identifier="Body",
            element=element,
            directrix=directrix,
            stylename="courtyard",
            path_dxf="molior/style/share/courtyard/eaves_corona.dxf",
            transform=transform,
        )

        run(
            "geometry.edit_object_placement",
            ifc,
            product=element,
            matrix=matrix_align([0.0, 0.0, 1.0], [1.0, 0.0, 1.0]),
        )
        assign_storey_byindex(ifc, element, building, 0)

        ifc.write("_test.ifc")

    def test_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
