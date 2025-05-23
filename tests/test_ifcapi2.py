#!/usr/bin/python3

import os
import sys
import pytest
import ifcopenshell.api.root

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_site_by_name,
    get_building_by_name,
    create_storeys,
    create_extruded_area_solid,
    assign_storey_byindex,
    get_type_object,
    get_context_by_name,
)
from molior.style import Style
from molior.geometry import matrix_align

api = ifcopenshell.api


@pytest.fixture
def setup_ifc_model():
    ifc = molior.ifc.init(name="My Project")
    body_context = get_context_by_name(ifc, context_identifier="Body")

    project = ifc.by_type("IfcProject")[0]
    style_object = Style()
    site = get_site_by_name(ifc, project, "My Site")
    building = get_building_by_name(ifc, site, "My Building")
    create_storeys(ifc, building, {0.0: 0})

    # create a window
    myproduct = api.root.create_entity(
        ifc,
        ifc_class="IfcWindow",
        name="My Window",
    )
    # window needs some attributes
    api.attribute.edit_attributes(
        ifc,
        product=myproduct,
        attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
    )
    # place the window in space
    api.geometry.edit_object_placement(
        ifc,
        product=myproduct,
        matrix=matrix_align([11.0, 0.0, 3.0], [11.0, 2.0, 0.0]),
    )
    # assign the window to a storey
    assign_storey_byindex(ifc, myproduct, building, 0)

    # load type and assign to the window
    product_type = get_type_object(
        ifc,
        style_object,
        ifc_type="IfcWindowType",
        stylename="default",
        name="shopfront",
    )
    api.type.assign_type(
        ifc,
        related_objects=[myproduct],
        relating_type=product_type,
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
                    ifc,
                    [[0.0, -0.25], [12.0, -0.25], [12.0, 0.08], [0.0, 0.08]],
                    4.0,
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
    # associate the opening with our window
    api.feature.add_filling(ifc, opening=myopening, element=myproduct)

    # create another window
    myproduct = api.root.create_entity(
        ifc,
        ifc_class="IfcWindow",
        name="Another Window",
    )
    # window needs some attributes
    api.attribute.edit_attributes(
        ifc,
        product=myproduct,
        attributes={"OverallHeight": 2.545, "OverallWidth": 5.0},
    )
    # place the window in space
    api.geometry.edit_object_placement(
        ifc,
        product=myproduct,
        matrix=matrix_align([11.0, 6.0, 3.0], [11.0, 9.0, 0.0]),
    )
    # assign the window to a storey
    assign_storey_byindex(ifc, myproduct, building, 0)

    # 'shopfront' is already imported and mapped
    product_type = get_type_object(
        ifc,
        style_object,
        ifc_type="IfcWindowType",
        stylename="default",
        name="shopfront",
    )
    api.type.assign_type(
        ifc,
        related_objects=[myproduct],
        relating_type=product_type,
    )

    # create an opening
    myopening = api.root.create_entity(
        ifc,
        ifc_class="IfcOpeningElement",
        name="Another Opening",
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
        matrix=matrix_align([11.0, 5.5, 3.0], [11.0, 9.0, 0.0]),
    )
    # use the opening to cut the wall, no need to assign a storey
    api.feature.add_feature(ifc, feature=myopening, element=mywall)
    # associate the opening with our window
    api.feature.add_filling(ifc, opening=myopening, element=myproduct)

    ifc.write("_test.ifc")

    return ifc


def test_noop(setup_ifc_model):
    # This test simply verifies the fixture setup completes without errors
    assert setup_ifc_model is not None


if __name__ == "__main__":
    pytest.main()
