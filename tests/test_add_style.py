import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ifcopenshell
import molior.ifc
from molior.ifc import create_extruded_area_solid, get_context_by_name

api = ifcopenshell.api


@pytest.fixture
def ifc_file():
    """Fixture to create and return an IFC file for testing"""
    file = molior.ifc.init(name="Our Project")
    body_context = get_context_by_name(file, context_identifier="Body")
    return file, body_context


def test_add_surface_style(ifc_file):
    file, body_context = ifc_file

    # Add style and surface style
    style = api.style.add_style(file, name="Outdoor wall")
    api.style.add_surface_style(
        file,
        style=style,
        ifc_class="IfcSurfaceStyleShading",
        attributes={
            "SurfaceColour": {
                "Name": "Orange",
                "Red": 1.0,
                "Green": 0.5,
                "Blue": 0.0,
            },
            "Transparency": 0.9,
        },
    )

    # Create shape representation
    shape = file.createIfcShapeRepresentation(
        body_context,
        body_context.ContextIdentifier,
        "SweptSolid",
        [create_extruded_area_solid(file, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0)],
    )

    # Assign styles to representation
    api.style.assign_representation_styles(
        file,
        shape_representation=shape,
        styles=[style],
    )

    # Create slab and assign representation
    slab = api.root.create_entity(file, ifc_class="IfcSlab", name="My Slab")
    api.geometry.assign_representation(
        file,
        product=slab,
        representation=shape,
    )

    # Assertions
    assert slab.Representation.is_a() == "IfcProductDefinitionShape"
    assert len(slab.Representation.Representations) == 1

    representation = slab.Representation.Representations[0]
    assert len(representation.Items) == 1

    myshape = representation.Items[0]
    styled_item = None
    for value in file.get_inverse(myshape):
        if value.is_a("IfcStyledItem"):
            styled_item = value
            break

    assert styled_item is not None
    style = styled_item.Styles[0]
    assert style.is_a() == "IfcSurfaceStyle"

    rendering = style.Styles[0]
    assert rendering.is_a() == "IfcSurfaceStyleShading"
    assert rendering.SurfaceColour.Name == "Orange"

    # Write the file
    file.write("_test.ifc")
