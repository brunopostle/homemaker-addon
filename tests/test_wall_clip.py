#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = molior.ifc.init("Our House", {0.0: 2})
        for item in ifc.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Body":
                body_context = item

        # geometry for an unclipped wall
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

        clipped = ifc.createIfcBooleanClippingResult(
            "DIFFERENCE",
            shape,
            ifc.createIfcPolygonalBoundedHalfSpace(
                ifc.createIfcPlane(
                    ifc.createIfcAxis2Placement3D(
                        ifc.createIfcCartesianPoint((2.5, 1.0, 2.0)),
                        ifc.createIfcDirection((0.6, 0.0, 0.8)),
                        None,
                    )
                ),
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
            ),
        )
        clipped2 = ifc.createIfcBooleanClippingResult(
            "DIFFERENCE",
            clipped,
            ifc.createIfcPolygonalBoundedHalfSpace(
                ifc.createIfcPlane(
                    ifc.createIfcAxis2Placement3D(
                        ifc.createIfcCartesianPoint((3.5, 1.0, 2.0)),
                        ifc.createIfcDirection((-0.6, 0.0, 0.8)),
                        None,
                    )
                ),
                False,
                ifc.createIfcAxis2Placement3D(
                    ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
                ),
                ifc.createIfcPolyline(
                    [
                        ifc.createIfcCartesianPoint(point)
                        for point in [
                            [3.0, 0.0],
                            [4.0, 0.0],
                            [4.0, 2.0],
                            [3.0, 2.0],
                            [3.0, 0.0],
                        ]
                    ]
                ),
            ),
        )
        clipped_representation = ifc.createIfcShapeRepresentation(
            body_context,
            "Body",
            "Clipping",
            [clipped2],
        )

        # use clipped geometry as a wall
        mywall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
        run(
            "geometry.assign_representation",
            ifc,
            product=mywall,
            representation=clipped_representation,
        )
        ifc.assign_storey_byindex(mywall, 2)
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
