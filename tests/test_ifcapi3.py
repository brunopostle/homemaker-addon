#!/usr/bin/python3

import os
import sys
import numpy
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.geometry_2d import matrix_align

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = run("project.create_file")

        run("owner.add_person", ifc)
        run("owner.add_organisation", ifc)

        project = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcProject",
            name="My Project",
        )

        run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METERS"})

        run("context.add_context", ifc)
        bodycontext = run(
            "context.add_context",
            ifc,
            context="Model",
            bodycontext="Body",
            target_view="MODEL_VIEW",
        )

        # create and relate site, building and a storey
        site = run("root.create_entity", ifc, ifc_class="IfcSite", name="My Site")
        building = run(
            "root.create_entity", ifc, ifc_class="IfcBuilding", name="My Building"
        )
        storey = run(
            "root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="My Storey"
        )
        run("aggregate.assign_object", ifc, product=site, relating_object=project)
        run("aggregate.assign_object", ifc, product=building, relating_object=site)
        run("aggregate.assign_object", ifc, product=storey, relating_object=building)

        externalref = ifc.createClosedProfileDefs_fromDXF(
            bodycontext, "courtyard", "molior/share/courtyard/eaves.dxf"
        )

        axis = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        )
        directrix = [[5.0, 1.0], [8.0, 1.0], [5.0, 5.0]]

        shape2 = ifc.createIfcShapeRepresentation(
            bodycontext,
            "Body",
            "AdvancedSweptSolid",
            [
                ifc.createIfcSurfaceCurveSweptAreaSolid(
                    closedprofiledef,
                    axis,
                    ifc.createIfcPolyline(
                        [ifc.createIfcCartesianPoint(point) for point in directrix]
                    ),
                    0.0,
                    1.0,
                    ifc.createIfcPlane(axis),
                )
                for closedprofiledef in externalref.RelatedResourceObjects
            ],
        )

        loft = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingElementProxy",
            name="My Extrusion",
        )
        run("geometry.assign_representation", ifc, product=loft, representation=shape2)
        run("geometry.edit_object_placement", ifc, product=loft, matrix=numpy.eye(4))
        run("spatial.assign_container", ifc, product=loft, relating_structure=storey)

        # do it again
        axis = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        )
        directrix = [[5.0, 2.0], [5.0, 4.0], [2.0, 4.0], [2.0, 2.0], [5.0, 2.0]]
        polyline = ifc.createIfcPolyline(
            [ifc.createIfcCartesianPoint(point) for point in directrix]
        )
        plane = ifc.createIfcPlane(axis)
        shape2 = ifc.createIfcShapeRepresentation(
            bodycontext,
            "Body",
            "AdvancedSweptSolid",
            [
                ifc.createIfcSurfaceCurveSweptAreaSolid(
                    closedprofiledef,
                    axis,
                    polyline,
                    0.0,
                    1.0,
                    plane,
                )
                for closedprofiledef in externalref.RelatedResourceObjects
            ],
        )

        loft = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingElementProxy",
            name="My Extrusion",
        )
        run("geometry.assign_representation", ifc, product=loft, representation=shape2)
        run("geometry.edit_object_placement", ifc, product=loft, matrix=numpy.eye(4))
        run("spatial.assign_container", ifc, product=loft, relating_structure=storey)

        # do it again, hopefully dxf isn't reloaded

        externalref = ifc.createClosedProfileDefs_fromDXF(
            bodycontext, "courtyard", "molior/share/courtyard/eaves.dxf"
        )

        axis = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        )
        directrix = [[-5.0, 1.0], [-1.0, 1.0], [-1.0, 5.0], [-5.0, 5.0], [-5.0, 1.0]]
        polyline = ifc.createIfcPolyline(
            [ifc.createIfcCartesianPoint(point) for point in directrix]
        )
        plane = ifc.createIfcPlane(axis)
        shape2 = ifc.createIfcShapeRepresentation(
            bodycontext,
            "Body",
            "AdvancedSweptSolid",
            [
                ifc.createIfcSurfaceCurveSweptAreaSolid(
                    closedprofiledef,
                    axis,
                    polyline,
                    0.0,
                    1.0,
                    plane,
                )
                for closedprofiledef in externalref.RelatedResourceObjects
            ],
        )

        loft = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingElementProxy",
            name="My Extrusion",
        )
        run("geometry.assign_representation", ifc, product=loft, representation=shape2)
        run("geometry.edit_object_placement", ifc, product=loft, matrix=numpy.eye(4))
        run("spatial.assign_container", ifc, product=loft, relating_structure=storey)

        ifc.write("_test.ifc")

    def test_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
