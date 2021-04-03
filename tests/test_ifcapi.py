#!/usr/bin/python3

import os
import sys
import unittest
import numpy
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc


class Tests(unittest.TestCase):
    def setUp(self):
        run = ifcopenshell.api.run

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

        shape = ifc.createSweptSolid(
            subcontext, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0
        )
        slab = run("root.create_entity", ifc, ifc_class="IfcSlab", name="My Slab")
        run("geometry.assign_representation", ifc, product=slab, representation=shape)
        run("geometry.edit_object_placement", ifc, product=slab, matrix=numpy.eye(4))
        run("spatial.assign_container", ifc, product=slab, relating_structure=storey)

        self.ifc = ifc

    def test_write(self):
        self.ifc.write("_test.ifc")
        pass


if __name__ == "__main__":
    unittest.main()
