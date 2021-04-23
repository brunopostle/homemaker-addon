#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.geometry_2d import matrix_align

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = molior.ifc.init("Our House", {0.0: 2})
        for item in ifc.by_type("IfcGeometricRepresentationSubContext"):
            if item.TargetView == "MODEL_VIEW":
                context = item

        shape = ifc.createIfcExtrudedAreaSolid(
            ifc.createIfcArbitraryClosedProfileDef(
                "AREA",
                None,
                ifc.createIfcPolyline(
                    [
                        ifc.createIfcCartesianPoint(point)
                        for point in [[1.0, 1.0], [4.0, 1.0], [4.0, 1.5], [1.0, 1.5]]
                    ]
                ),
            ),
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
            ),
            ifc.createIfcDirection([0.0, 0.0, 1.0]),
            3.0,
        )

        plane = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((2.5, 1.0, 2.0)),
            ifc.createIfcDirection((0.6, 0.0, 0.8)),
            ifc.createIfcDirection((0.0, 1.0, 0.0)),
        )
        polyhalfsolid = ifc.createIfcPolygonalBoundedHalfSpace(
            ifc.createIfcPlane(plane),
            False,
            ifc.createIfcAxis2Placement3D(
                ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
            ),
            ifc.createIfcPolyline(
                [
                    ifc.createIfcCartesianPoint(point)
                    for point in [
                        [2.0, 0.0],
                        [3.0, 0.0],
                        [3.0, 2.0],
                        [2.0, 2.0],
                        [2.0, 0.0],
                    ]
                ]
            ),
        )
        clipped = ifc.createIfcBooleanClippingResult(
            "DIFFERENCE",
            shape,
            polyhalfsolid,
        )
        clipped_representation = ifc.createIfcShapeRepresentation(
            context,
            "Body",
            "Clipping",
            [clipped],
        )

        # use clipped geometry as a wall
        mywall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
        ifc.assign_storey_byindex(mywall, 2)
        run(
            "geometry.assign_representation",
            ifc,
            product=mywall,
            representation=clipped_representation,
        )
        run(
            "geometry.edit_object_placement",
            ifc,
            product=mywall,
            matrix=matrix_align([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]),
        )
        ifc.write("_test.ifc")

    def test_sanity(self):
        pass


if __name__ == "__main__":
    unittest.main()
