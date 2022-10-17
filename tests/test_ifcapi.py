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
    get_type_object,
    create_storeys,
    create_extruded_area_solid,
    assign_storey_byindex,
    get_context_by_name,
)
from molior.style import Style
from molior.geometry import matrix_transform, matrix_align

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        ifc = molior.ifc.init(name="My Project")
        self.body_context = get_context_by_name(ifc, context_identifier="Body")
        self.axis_context = get_context_by_name(ifc, context_identifier="Axis")
        self.style_object = Style()

        project = ifc.by_type("IfcProject")[0]
        site = get_site_by_name(ifc, project, "My Site")
        self.building = get_building_by_name(ifc, site, "My Building")
        create_storeys(ifc, self.building, {0.0: 0})

        # a centreline axis
        poly = ifc.createIfcShapeRepresentation(
            self.axis_context,
            "Axis",
            "Curve2D",
            [
                ifc.createIfcPolyline(
                    [
                        ifc.createIfcCartesianPoint(point)
                        for point in [[1.0, 0.0], [1.0, -3.0], [3.0, -3.0]]
                    ]
                )
            ],
        )

        wall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
        run("geometry.assign_representation", ifc, product=wall, representation=poly)
        assign_storey_byindex(ifc, wall, self.building, 0)

        # a vertically extruded solid
        shape = ifc.createIfcShapeRepresentation(
            self.body_context,
            self.body_context.ContextIdentifier,
            "SweptSolid",
            [
                create_extruded_area_solid(
                    ifc, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0
                )
            ],
        )
        slab = run("root.create_entity", ifc, ifc_class="IfcSlab", name="My Slab")
        run("geometry.assign_representation", ifc, product=slab, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=slab,
            matrix=matrix_align([3.0, 0.0, 3.0], [4.0, 1.0, 3.0]),
        )
        assign_storey_byindex(ifc, slab, self.building, 0)

        product_type = get_type_object(
            ifc,
            self.style_object,
            ifc_type="IfcDoorType",
            stylename="default",
            name="shopfront",
        )

        # create a door using the mapped item
        door = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcDoor",
            name="My Door",
        )
        run(
            "attribute.edit_attributes",
            ifc,
            product=door,
            attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
        )
        run(
            "type.assign_type",
            ifc,
            related_object=door,
            relating_type=product_type,
        )
        # place it in space and assign to storey
        run(
            "geometry.edit_object_placement",
            ifc,
            product=door,
            matrix=matrix_transform(0.0, [15.0, 0.0, 0.0]),
        )
        assign_storey_byindex(ifc, door, self.building, 0)

        # create another door using the mapped item
        door2 = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcDoor",
            name="My Door",
        )
        run(
            "attribute.edit_attributes",
            ifc,
            product=door2,
            attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
        )
        run(
            "type.assign_type",
            ifc,
            related_object=door2,
            relating_type=product_type,
        )
        # place it in space and assign to storey
        run(
            "geometry.edit_object_placement",
            ifc,
            product=door2,
            matrix=matrix_align([11.0, 0.0, 0.0], [11.0, 2.0, 0.0]),
        )
        assign_storey_byindex(ifc, door2, self.building, 0)

        # make the ifc model available to other test methods
        self.ifc = ifc

    def test_write(self):
        ifc = self.ifc
        # create a lookup table of existing typeproducts in this ifc
        lookup = {}
        for typeproduct in ifc.by_type("IfcTypeProduct"):
            lookup[typeproduct.Name] = typeproduct

        # create a door
        myproduct = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcDoor",
            name="My Door",
        )
        # door needs some attributes
        run(
            "attribute.edit_attributes",
            ifc,
            product=myproduct,
            attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
        )
        # place the door in space
        run(
            "geometry.edit_object_placement",
            ifc,
            product=myproduct,
            matrix=matrix_align([11.0, 0.0, 3.0], [11.0, 2.0, 0.0]),
        )
        # assign the door to a storey
        assign_storey_byindex(ifc, myproduct, self.building, 0)

        # The TypeProduct knows what MappedRepresentations to use
        typeproduct = lookup["shopfront"]
        for representationmap in typeproduct.RepresentationMaps:
            run(
                "geometry.assign_representation",
                ifc,
                product=myproduct,
                representation=run(
                    "geometry.map_representation",
                    ifc,
                    representation=representationmap.MappedRepresentation,
                ),
            )

        # create a wall
        mywall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
        # give the wall a Body representation
        run(
            "geometry.assign_representation",
            ifc,
            product=mywall,
            representation=ifc.createIfcShapeRepresentation(
                self.body_context,
                self.body_context.ContextIdentifier,
                "SweptSolid",
                [
                    create_extruded_area_solid(
                        ifc, [[0.0, -0.25], [6.0, -0.25], [6.0, 0.08], [0.0, 0.08]], 4.0
                    )
                ],
            ),
        )

        # place the wall in space
        run(
            "geometry.edit_object_placement",
            ifc,
            product=mywall,
            matrix=matrix_align([11.0, -0.5, 3.0], [11.0, 2.0, 0.0]),
        )
        # assign the wall to a storey
        assign_storey_byindex(ifc, mywall, self.building, 0)

        # create an opening
        myopening = run(
            "root.create_entity", ifc, ifc_class="IfcOpeningElement", name="My Opening"
        )
        run(
            "attribute.edit_attributes",
            ifc,
            product=myopening,
            attributes={"PredefinedType": "OPENING"},
        )
        # give the opening a Body representation
        run(
            "geometry.assign_representation",
            ifc,
            product=myopening,
            representation=ifc.createIfcShapeRepresentation(
                self.body_context,
                self.body_context.ContextIdentifier,
                "SweptSolid",
                [
                    create_extruded_area_solid(
                        ifc, [[0.5, -1.0], [5.5, -1.0], [5.5, 1.0], [0.5, 1.0]], 2.545
                    )
                ],
            ),
        )
        # place the opening where the wall is
        run(
            "geometry.edit_object_placement",
            ifc,
            product=myopening,
            matrix=matrix_align([11.0, -0.5, 3.0], [11.0, 2.0, 0.0]),
        )
        # use the opening to cut the wall, no need to assign a storey
        run("void.add_opening", ifc, opening=myopening, element=mywall)
        # associate the opening with our door
        run("void.add_filling", ifc, opening=myopening, element=myproduct)

        ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
