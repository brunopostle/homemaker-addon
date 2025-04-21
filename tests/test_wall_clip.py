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
    assign_storey_byindex,
    get_context_by_name,
)
from molior.geometry import matrix_align

api = ifcopenshell.api


@pytest.fixture
def ifc_model():
    """Fixture to set up the IFC model for testing"""
    ifc = molior.ifc.init(name="Our Project")
    body_context = get_context_by_name(ifc, context_identifier="Body")

    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site")
    building = get_building_by_name(ifc, site, "My Building")
    create_storeys(ifc, building, {0.0: 2})

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
        body_context.ContextIdentifier,
        "Clipping",
        [clipped2],
    )

    # use clipped geometry as a wall
    mywall = api.root.create_entity(ifc, ifc_class="IfcWall", name="My Wall")
    api.geometry.assign_representation(
        ifc,
        product=mywall,
        representation=clipped_representation,
    )
    assign_storey_byindex(ifc, mywall, building, 2)
    api.geometry.edit_object_placement(
        ifc,
        product=mywall,
        matrix=matrix_align([0.0, 0.0, 0.0], [1.0, 0.0, 0.0]),
    )
    ifc.write("_test.ifc")

    return ifc


def test_sanity(ifc_model):
    """Placeholder sanity test to ensure the IFC model can be created successfully"""
    assert ifc_model is not None
