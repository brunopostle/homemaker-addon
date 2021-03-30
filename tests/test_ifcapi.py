#!/usr/bin/python3

import os
import sys
import unittest
import numpy
import ifcopenshell.api


class Tests(unittest.TestCase):
    def setUp(self):
        run = ifcopenshell.api.run

        ifc = run("project.create_file")

        myperson = run("owner.add_person", ifc)
        myorganisation = run("owner.add_organisation", ifc)
        ownerhistory = run(
            "owner.create_owner_history",
            ifc,
            person=myperson,
            organisation=myorganisation,
        )  # doesn't seem to do anything

        project = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcProject",
            name="My Project",
        )

        run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METERS"})

        mycontext = run("context.add_context", ifc)
        subcontext = run(
            "context.add_context",
            ifc,
            context="Model",
            subcontext="Body",
            target_view="MODEL_VIEW",
        )

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

        # SLAB

        # create a sweptsolid:
        profile = ifc.createIfcArbitraryClosedProfileDef(
            "AREA",
            None,
            ifc.createIfcPolyline(
                [
                    ifc.createIfcCartesianPoint((1.0, 0.1)),
                    ifc.createIfcCartesianPoint((4.0, 0.2)),
                    ifc.createIfcCartesianPoint((4.0, 3.1)),
                    ifc.createIfcCartesianPoint((1.0, 3.1)),
                    ifc.createIfcCartesianPoint((1.0, 0.1)),
                ]
            ),
        )
        axis = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        )
        direction = ifc.createIfcDirection([0.0, 0.0, 1.0])
        solid = ifc.createIfcExtrudedAreaSolid(profile, axis, direction, 0.5)
        shape = ifc.createIfcShapeRepresentation(
            subcontext, "Body", "SweptSolid", [solid]
        )

        # localplacement? this isn't used
        # how do we use the storey origin?
        shift = ifc.createIfcAxis2Placement3D(
            ifc.createIfcCartesianPoint((0.0, 0.0, 3.0)), None, None
        )
        localplacement = ifc.createIfcLocalPlacement(axis, shift)

        slab = run("root.create_entity", ifc, ifc_class="IfcSlab", name="My Slab")
        run("geometry.assign_representation", ifc, product=slab, representation=shape)
        run("geometry.edit_object_placement", ifc, product=slab, matrix=numpy.eye(4))

        run("spatial.assign_container", ifc, product=slab, relating_structure=storey)

        self.ifc = ifc

    def test_write(self):
        # self.ifc.write("test.ifc")
        pass


if __name__ == "__main__":
    unittest.main()
