#!/usr/bin/python3

import os
import sys
import unittest
import numpy
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.geometry_2d import matrix_transform, matrix_align


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

        # a centreline axis
        poly = ifc.createCurve2D(subcontext, [[1.0, 0.0], [1.0, -3.0], [3.0, -3.0]])
        wall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
        run("geometry.assign_representation", ifc, product=wall, representation=poly)
        run("spatial.assign_container", ifc, product=wall, relating_structure=storey)

        # a vertically extruded solid
        shape = ifc.createSweptSolid(
            subcontext, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0
        )
        slab = run("root.create_entity", ifc, ifc_class="IfcSlab", name="My Slab")
        run("geometry.assign_representation", ifc, product=slab, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=slab,
            matrix=matrix_align([3.0, 0.0, 3.0], [4.0, 1.0, 3.0]),
        )
        run("spatial.assign_container", ifc, product=slab, relating_structure=storey)

        # an extrusion that follows a 2D directrix
        shape2 = ifc.createAdvancedSweptSolid(
            subcontext,
            [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0]],
            [[5.0, 1.0], [8.0, 1.0], [5.0, 5.0]],
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

        # load a DXF polyface mesh as a Brep
        brep = ifc.createBrep_fromDXF(
            subcontext,
            "molior/share/shopfront.dxf",
        )
        # create a mapped item that can be reused
        run(
            "geometry.assign_representation",
            ifc,
            product=run(
                "root.create_entity",
                ifc,
                ifc_class="IfcTypeProduct",
                name="shopfront.dxf",
            ),
            representation=brep,
        )
        mapped_shopfront = run("geometry.map_representation", ifc, representation=brep)

        # create a window using the mapped item
        window = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcWindow",
            name="My Window",
        )
        run(
            "geometry.assign_representation",
            ifc,
            product=window,
            representation=mapped_shopfront,
        )
        # place it in space and assign to storey
        run(
            "geometry.edit_object_placement",
            ifc,
            product=window,
            matrix=matrix_transform(0.0, [15.0, 0.0, 0.0]),
        )
        run("spatial.assign_container", ifc, product=window, relating_structure=storey)

        # create another window using the mapped item
        window2 = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcWindow",
            name="Another Window",
        )
        run(
            "geometry.assign_representation",
            ifc,
            product=window2,
            representation=mapped_shopfront,
        )
        # place it in space and assign to storey
        run(
            "geometry.edit_object_placement",
            ifc,
            product=window2,
            matrix=matrix_align([11.0, 0.0, 0.0], [11.0, 2.0, 0.0]),
        )
        run("spatial.assign_container", ifc, product=window2, relating_structure=storey)

        # load a DXF polyface mesh as a Tessellation
        tessellation = ifc.createTessellation_fromDXF(
            subcontext,
            "molior/share/shopfront.dxf",
        )
        # create a window using the tessellation (not a mapped typeproduct)
        window3 = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcWindow",
            name="My Window",
        )
        run(
            "geometry.assign_representation",
            ifc,
            product=window3,
            representation=tessellation,
        )
        run(
            "geometry.edit_object_placement",
            ifc,
            product=window3,
            matrix=matrix_transform(0.0, [5.0, 0.0, 0.0]),
        )
        run("spatial.assign_container", ifc, product=window3, relating_structure=storey)

        # make the ifc model available to other test methods
        self.ifc = ifc

    def test_write(self):
        self.ifc.write("_test.ifc")
        pass


if __name__ == "__main__":
    unittest.main()
