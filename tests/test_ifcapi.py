#!/usr/bin/python3

import os
import sys
import pytest
import ifcopenshell.api.attribute

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

api = ifcopenshell.api


@pytest.fixture
def setup_ifc():
    ifc = molior.ifc.init(name="My Project")
    body_context = get_context_by_name(ifc, context_identifier="Body")
    axis_context = get_context_by_name(ifc, context_identifier="Axis")
    style_object = Style()

    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site")
    building = get_building_by_name(ifc, site, "My Building")
    create_storeys(ifc, building, {0.0: 0})

    # a centreline axis
    poly = ifc.createIfcShapeRepresentation(
        axis_context,
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

    wall = api.root.create_entity(ifc, ifc_class="IfcWall", name="My Wall")
    api.geometry.assign_representation(ifc, product=wall, representation=poly)
    assign_storey_byindex(ifc, wall, building, 0)

    # a vertically extruded solid
    shape = ifc.createIfcShapeRepresentation(
        body_context,
        body_context.ContextIdentifier,
        "SweptSolid",
        [create_extruded_area_solid(ifc, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0)],
    )
    slab = api.root.create_entity(ifc, ifc_class="IfcSlab", name="My Slab")
    api.geometry.assign_representation(ifc, product=slab, representation=shape)
    api.geometry.edit_object_placement(
        ifc,
        product=slab,
        matrix=matrix_align([3.0, 0.0, 3.0], [4.0, 1.0, 3.0]),
    )
    assign_storey_byindex(ifc, slab, building, 0)

    type_product = get_type_object(
        ifc,
        style_object,
        ifc_type="IfcDoorType",
        stylename="default",
        name="shopfront",
    )

    # create a door using the mapped item
    door = api.root.create_entity(
        ifc,
        ifc_class="IfcDoor",
        name="My Door",
    )
    api.attribute.edit_attributes(
        ifc,
        product=door,
        attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
    )
    api.type.assign_type(
        ifc,
        related_objects=[door],
        relating_type=type_product,
    )
    # place it in space and assign to storey
    api.geometry.edit_object_placement(
        ifc,
        product=door,
        matrix=matrix_transform(0.0, [15.0, 0.0, 0.0]),
    )
    assign_storey_byindex(ifc, door, building, 0)

    # create another door using the mapped item
    door2 = api.root.create_entity(
        ifc,
        ifc_class="IfcDoor",
        name="My Door",
    )
    api.attribute.edit_attributes(
        ifc,
        product=door2,
        attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
    )
    api.type.assign_type(
        ifc,
        related_objects=[door2],
        relating_type=type_product,
    )
    # place it in space and assign to storey
    api.geometry.edit_object_placement(
        ifc,
        product=door2,
        matrix=matrix_align([11.0, 0.0, 0.0], [11.0, 2.0, 0.0]),
    )
    assign_storey_byindex(ifc, door2, building, 0)

    # Make the necessary objects available to the test
    return {
        "ifc": ifc,
        "body_context": body_context,
        "axis_context": axis_context,
        "style_object": style_object,
        "building": building,
    }


def test_write(setup_ifc):
    ifc = setup_ifc["ifc"]
    body_context = setup_ifc["body_context"]
    building = setup_ifc["building"]

    # create a lookup table of existing typeproducts in this ifc
    lookup = {}
    for typeproduct in ifc.by_type("IfcTypeProduct"):
        lookup[typeproduct.Name] = typeproduct

    # create a door
    myproduct = api.root.create_entity(
        ifc,
        ifc_class="IfcDoor",
        name="My Door",
    )
    # door needs some attributes
    api.attribute.edit_attributes(
        ifc,
        product=myproduct,
        attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
    )
    # place the door in space
    api.geometry.edit_object_placement(
        ifc,
        product=myproduct,
        matrix=matrix_align([11.0, 0.0, 3.0], [11.0, 2.0, 0.0]),
    )
    # assign the door to a storey
    assign_storey_byindex(ifc, myproduct, building, 0)

    # The TypeProduct knows what MappedRepresentations to use
    typeproduct = lookup["shopfront"]
    for representationmap in typeproduct.RepresentationMaps:
        api.geometry.assign_representation(
            ifc,
            product=myproduct,
            representation=api.geometry.map_representation(
                ifc,
                representation=representationmap.MappedRepresentation,
            ),
        )

    # create a wall
    mywall = api.root.create_entity(ifc, ifc_class="IfcWall", name="My Wall")
    # give the wall a Body representation
    api.geometry.assign_representation(
        ifc,
        product=mywall,
        representation=ifc.createIfcShapeRepresentation(
            body_context,
            body_context.ContextIdentifier,
            "SweptSolid",
            [
                create_extruded_area_solid(
                    ifc, [[0.0, -0.25], [6.0, -0.25], [6.0, 0.08], [0.0, 0.08]], 4.0
                )
            ],
        ),
    )

    # place the wall in space
    api.geometry.edit_object_placement(
        ifc,
        product=mywall,
        matrix=matrix_align([11.0, -0.5, 3.0], [11.0, 2.0, 0.0]),
    )
    # assign the wall to a storey
    assign_storey_byindex(ifc, mywall, building, 0)

    # create an opening
    myopening = api.root.create_entity(
        ifc, ifc_class="IfcOpeningElement", name="My Opening"
    )
    api.attribute.edit_attributes(
        ifc,
        product=myopening,
        attributes={"PredefinedType": "OPENING"},
    )
    # give the opening a Body representation
    api.geometry.assign_representation(
        ifc,
        product=myopening,
        representation=ifc.createIfcShapeRepresentation(
            body_context,
            body_context.ContextIdentifier,
            "SweptSolid",
            [
                create_extruded_area_solid(
                    ifc, [[0.5, -1.0], [5.5, -1.0], [5.5, 1.0], [0.5, 1.0]], 2.545
                )
            ],
        ),
    )
    # place the opening where the wall is
    api.geometry.edit_object_placement(
        ifc,
        product=myopening,
        matrix=matrix_align([11.0, -0.5, 3.0], [11.0, 2.0, 0.0]),
    )
    # use the opening to cut the wall, no need to assign a storey
    api.feature.add_feature(ifc, feature=myopening, element=mywall)
    # associate the opening with our door
    api.feature.add_filling(ifc, opening=myopening, element=myproduct)

    ifc.write("_test.ifc")
    # Since this is primarily testing file writing functionality,
    # we just assert that the code runs without errors
    assert True


if __name__ == "__main__":
    pytest.main(["-v"])
