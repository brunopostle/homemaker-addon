#!/usr/bin/python3

import os
import sys
import numpy
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    create_site,
    create_building,
    create_storeys,
    assign_storey_byindex,
    assign_extrusion_fromDXF,
)
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = molior.ifc.init(name="My Project")
        for item in ifc.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Body":
                body_context = item

        project = ifc.by_type("IfcProject")[0]
        site = create_site(ifc, project, "My Site")
        building = create_building(ifc, site, "My Building")
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
            body_context,
            element,
            directrix,
            "courtyard",
            "molior/style/share/courtyard/eaves.dxf",
            transform,
        )

        run("geometry.edit_object_placement", ifc, product=element, matrix=numpy.eye(4))
        assign_storey_byindex(ifc, element, 0)

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
            body_context,
            element,
            directrix,
            "courtyard",
            "molior/style/share/courtyard/eaves.dxf",
            transform,
        )

        run(
            "geometry.edit_object_placement",
            ifc,
            product=element,
            matrix=matrix_align([0.0, 0.0, 1.0], [1.0, 0.0, 1.0]),
        )
        assign_storey_byindex(ifc, element, 0)

        ifc.write("_test.ifc")

    def test_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
