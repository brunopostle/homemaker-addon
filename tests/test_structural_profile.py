"""Tests for the Profile and Material of Structural Curve Members."""

import os
import sys

import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import molior.ifc
from molior.ifc import assign_structural_profile, get_structural_layer, is_load_bearing
from molior.style import Style

api = ifcopenshell.api


@pytest.fixture
def ifc():
    return molior.ifc.init(name="My Project")


@pytest.fixture
def style():
    return Style({"share_dir": os.path.join(ROOT, "share")})


def member_type(ifc, profile, young_modulus=None):
    """An IfcMemberType with a Profile Set of a Material, with or without stiffness"""
    material = api.material.add_material(ifc, name="Some timber")
    if young_modulus:
        pset = api.pset.add_pset(ifc, product=material, name="Pset_MaterialMechanical")
        api.pset.edit_pset(ifc, pset=pset, properties={"YoungModulus": young_modulus})
    type_product = api.root.create_entity(ifc, ifc_class="IfcMemberType")
    rel = api.material.assign_material(
        ifc, products=[type_product], type="IfcMaterialProfileSet"
    )
    material_profile = api.material.add_profile(
        ifc, profile_set=rel.RelatingMaterial, material=material
    )
    api.material.assign_profile(ifc, material_profile=material_profile, profile=profile)
    return type_product


def type_product_material(type_product):
    return type_product.HasAssociations[0].RelatingMaterial.MaterialProfiles[0].Material


def profile_and_material(member):
    (association,) = member.HasAssociations
    (material_profile,) = association.RelatingMaterial.MaterialProfiles
    return material_profile.Profile, material_profile.Material


def test_profile_and_material_from_the_type(ifc, style):
    profile = ifc.createIfcRectangleProfileDef("AREA", "CLS 2x6", None, 0.038, 0.14)
    type_product = member_type(ifc, profile, young_modulus=11e9)
    member = api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
    assign_structural_profile(ifc, member, type_product, style)
    assert profile_and_material(member) == (
        profile,
        type_product_material(type_product),
    )


def test_style_overrides_the_type(ifc, style):
    profile = ifc.createIfcRectangleProfileDef("AREA", "CLS 2x6", None, 0.038, 0.14)
    type_product = member_type(ifc, profile, young_modulus=11e9)
    member = api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
    assign_structural_profile(
        ifc,
        member,
        type_product,
        style,
        profile=["IfcCircleProfileDef", {"ProfileType": "AREA", "Radius": 0.1}],
        material="Masonry",
    )
    profile, material = profile_and_material(member)
    assert profile.is_a("IfcCircleProfileDef")
    assert profile.Radius == 0.1
    assert material.Name == "Masonry"


def test_moulding_and_material_without_stiffness_are_not_used(ifc, style):
    outline = ifc.createIfcArbitraryClosedProfileDef(
        "AREA",
        "moulding",
        ifc.createIfcPolyline(
            [
                ifc.createIfcCartesianPoint(point)
                for point in ((0.0, 0.0), (0.3, 0.0), (0.3, 0.1), (0.0, 0.0))
            ]
        ),
    )
    type_product = member_type(ifc, outline)
    member = api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
    default = [
        "IfcRectangleProfileDef",
        {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.3},
    ]
    assign_structural_profile(ifc, member, type_product, style, default_profile=default)
    profile, material = profile_and_material(member)
    assert profile.is_a("IfcRectangleProfileDef")
    assert (profile.XDim, profile.YDim) == (0.2, 0.3)
    assert material.Name == "Concrete"


def test_no_type(ifc, style):
    member = api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
    assign_structural_profile(ifc, member, None, style)
    profile, material = profile_and_material(member)
    assert (profile.XDim, profile.YDim) == (0.2, 0.2)
    assert material.Name == "Concrete"


def layered_type(ifc, layers, ifc_class="IfcWallType"):
    """A Type with a Layer Set of (name, thickness, young_modulus) layers"""
    type_product = api.root.create_entity(ifc, ifc_class=ifc_class)
    rel = api.material.assign_material(
        ifc, products=[type_product], type="IfcMaterialLayerSet"
    )
    for name, thickness, young_modulus in layers:
        material = api.material.add_material(ifc, name=name)
        if young_modulus:
            pset = api.pset.add_pset(
                ifc, product=material, name="Pset_MaterialMechanical"
            )
            api.pset.edit_pset(
                ifc, pset=pset, properties={"YoungModulus": young_modulus}
            )
        layer = api.material.add_layer(
            ifc, layer_set=rel.RelatingMaterial, material=material
        )
        layer.LayerThickness = thickness
    return type_product


def test_load_bearing_unless_the_type_says_not(ifc):
    type_product = api.root.create_entity(ifc, ifc_class="IfcWallType")
    assert is_load_bearing(None)
    assert is_load_bearing(type_product)
    pset = api.pset.add_pset(ifc, product=type_product, name="Pset_WallCommon")
    api.pset.edit_pset(ifc, pset=pset, properties={"LoadBearing": True})
    assert is_load_bearing(type_product)
    api.pset.edit_pset(ifc, pset=pset, properties={"LoadBearing": False})
    assert not is_load_bearing(type_product)


def test_structural_layer_is_the_thickest_with_stiffness(ifc, style):
    type_product = layered_type(
        ifc,
        [("Brick", 0.1, 5e9), ("Insulation", 0.15, None), ("Block", 0.14, 5e9)],
    )
    material, thickness = get_structural_layer(ifc, type_product, style)
    assert (material.Name, thickness) == ("Block", 0.14)


def test_structural_layer_from_the_style(ifc, style):
    type_product = layered_type(ifc, [("Block", 0.14, 5e9)])
    material, thickness = get_structural_layer(
        ifc, type_product, style, material="Masonry", thickness=0.3
    )
    assert (material.Name, thickness) == ("Masonry", 0.3)
    # the material named, the thickness of the layer
    material, thickness = get_structural_layer(
        ifc, type_product, style, material="Masonry"
    )
    assert (material.Name, thickness) == ("Masonry", 0.14)


def test_structural_layer_without_stiffness(ifc, style):
    type_product = layered_type(ifc, [("Plaster", 0.03, None), ("Tiles", 0.05, None)])
    material, thickness = get_structural_layer(
        ifc, type_product, style, default_material="Masonry"
    )
    assert (material.Name, thickness) == ("Masonry", 0.2)
    material, thickness = get_structural_layer(ifc, None, style)
    assert (material.Name, thickness) == ("Concrete", 0.2)
