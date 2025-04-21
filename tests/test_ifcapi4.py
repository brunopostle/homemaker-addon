#!/usr/bin/python3

import os
import sys
import pytest
import ifcopenshell.api.root
import ifcopenshell.util.element

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_context_by_name,
    add_pset,
    get_type_object,
)
from molior.style import Style

api = ifcopenshell.api


@pytest.fixture
def ifc_project():
    """Fixture to set up the primary IFC file."""
    file = molior.ifc.init(name="My Project")
    body_context = get_context_by_name(file, context_identifier="Body")

    column_type = get_type_object(
        file,
        Style(),
        ifc_type="IfcMemberType",
        stylename="framing",
        name="purlin",
    )

    mycolumn = api.root.create_entity(file, ifc_class="IfcColumn", name="My Column")
    api.type.assign_type(
        file,
        related_objects=[mycolumn],
        relating_type=column_type,
    )

    for material in file.by_type("IfcMaterial"):
        add_pset(file, material, "some pset name", {"foo": "bar"})

    # test copying materials
    another_file = molior.ifc.init(name="My Other Project")
    for entity in file.by_type("IfcMaterial"):
        api.project.append_asset(
            another_file,
            library=file,
            element=entity,
        )

    # an extruded solid
    shape = file.createIfcShapeRepresentation(
        body_context,
        body_context.ContextIdentifier,
        "SweptSolid",
        [
            file.createIfcExtrudedAreaSolid(
                material_profile.Profile,
                file.createIfcAxis2Placement3D(
                    file.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                    file.createIfcDirection([0.0, 1.0, 0.0]),
                    file.createIfcDirection([1.0, 0.0, 0.0]),
                ),
                file.createIfcDirection([0.0, 0.0, 1.0]),
                3.0,
            )
            for material_profile in column_type.HasAssociations[
                0
            ].RelatingMaterial.MaterialProfiles
        ],
    )
    api.geometry.assign_representation(
        file,
        product=mycolumn,
        representation=shape,
    )

    return file, another_file


def test_write(ifc_project):
    """Test writing the IFC file."""
    file, _ = ifc_project
    file.write("_test.ifc")


def test_copy_material(ifc_project):
    """Test copying materials between IFC files."""
    file, another_file = ifc_project

    # Check the number of geometric representation contexts
    assert len(file.by_type("IfcGeometricRepresentationContext")) == 13
    assert len(another_file.by_type("IfcGeometricRepresentationContext")) == 13

    # Validate material representations
    for material in another_file.by_type("IfcMaterial"):
        if material.Name == "Cheese":
            assert len(material.HasRepresentation) == 0
            continue

        assert len(material.HasRepresentation) == 1
        assert len(material.HasRepresentation[0].Representations) == 1
        assert len(material.HasRepresentation[0].Representations[0].Items) == 1
        assert (
            len(material.HasRepresentation[0].Representations[0].Items[0].Styles) == 1
        )
        assert (
            len(
                material.HasRepresentation[0]
                .Representations[0]
                .Items[0]
                .Styles[0]
                .Styles
            )
            == 1
        )
        assert (
            material.HasRepresentation[0]
            .Representations[0]
            .Items[0]
            .Styles[0]
            .Styles[0]
            .SurfaceColour.is_a()
        ) == "IfcColourRgb"
