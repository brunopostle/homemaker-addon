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
from molior.ifc import assign_structural_profile
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
