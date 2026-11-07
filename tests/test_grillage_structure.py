"""Tests for the structural members of the lines of a Grillage."""

import collections
import json
import os
import shutil
import subprocess
import sys

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# a timber frame room with a gabled roof, and one with a flat roof
DOCUMENT = {
    "rooms": [
        {
            "vertices": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "stylename": "framing",
            "usage": "living",
        },
        {
            "vertices": [[5, 0], [8, 0], [8, 4], [5, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "stylename": "framing",
            "usage": "kitchen",
        },
    ],
    "faces": [
        {"vertices": [[0, 0, 3], [5, 0, 3], [5, 2, 4.5], [0, 2, 4.5]]},
        {"vertices": [[5, 4, 3], [0, 4, 3], [0, 2, 4.5], [5, 2, 4.5]]},
        {"vertices": [[5, 0, 3], [5, 4, 3], [5, 2, 4.5]]},
        {"vertices": [[0, 4, 3], [0, 0, 3], [0, 2, 4.5]]},
    ],
}
for face in DOCUMENT["faces"]:
    face["stylename"] = "framing"


@pytest.fixture(scope="module")
def framing(tmp_path_factory):
    path = tmp_path_factory.mktemp("framing")
    (path / "framing.json").write_text(json.dumps(DOCUMENT))
    subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "rooms2ifc.py"),
            path / "framing.json",
            path / "framing.ifc",
        ],
        check=True,
        capture_output=True,
    )
    return path / "framing.ifc"


@pytest.fixture(scope="module")
def ifc(framing):
    return ifcopenshell.open(framing)


def ends(member):
    edge = member.Representation.Representations[0].Items[0]
    return [
        np.array(vertex.VertexGeometry.Coordinates)
        for vertex in (edge.EdgeStart, edge.EdgeEnd)
    ]


def element(member):
    (rel,) = member.ReferencedBy
    (element,) = rel.RelatedObjects
    return element


def test_grillage_lines_have_curve_members(ifc):
    members = collections.Counter(
        member.Name for member in ifc.by_type("IfcStructuralCurveMember")
    )
    for name in ("stud-external", "joist", "purlin", "nogging-flat-roof"):
        assert members["framing/" + name], name
    # every structural line is drawn as a member, and only once
    for item in ifc.by_type("IfcMember"):
        assigned = [
            rel for rel in item.HasAssignments if rel.is_a("IfcRelAssignsToProduct")
        ]
        assert len(assigned) == 1


def test_curve_members_have_the_section_of_their_type(ifc):
    for member in ifc.by_type("IfcStructuralCurveMember"):
        material_profile = ifcopenshell.util.element.get_material(member)
        material_profile = material_profile.MaterialProfiles[0]
        if member.Name == "framing/stud-external":
            assert material_profile.Profile.ProfileName == "CLS 2x6"
            assert material_profile.Material.Name == "C24 Wood"
        if member.Name == "framing/purlin":
            assert material_profile.Profile.is_a("IfcIShapeProfileDef")
            assert material_profile.Material.Name == "Hot Rolled Steel"


def test_curve_members_are_where_their_elements_are(ifc):
    """Members of a grillage within a grillage are moved twice, as their elements are"""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    checked = collections.Counter()
    for member in ifc.by_type("IfcStructuralCurveMember"):
        shape = ifcopenshell.geom.create_shape(settings, element(member))
        vertices = np.array(shape.geometry.verts).reshape(-1, 3)
        low, high = vertices.min(axis=0) - 0.15, vertices.max(axis=0) + 0.15
        start, end = ends(member)
        for point in (start, end, (start + end) / 2):
            assert (point >= low).all() and (point <= high).all(), member.Name
        checked[member.Name] += 1
    assert checked["framing/nogging-flat-roof"]


def test_axis_is_across_the_face(ifc):
    for member in ifc.by_type("IfcStructuralCurveMember"):
        start, end = ends(member)
        axis = np.array(member.Axis.DirectionRatios)
        assert abs(np.dot(axis, end - start)) < 1e-6
        if member.Name == "framing/stud-external":
            # studs are in walls, so the face normal is horizontal
            assert abs(axis[2]) < 1e-6


def test_no_structural_surfaces_for_grillages_or_their_infill(ifc):
    names = {member.Name for member in ifc.by_type("IfcStructuralSurfaceMember")}
    assert not [name for name in names if "studs" in name or "joists" in name]
    assert "framing/batten-insulation" not in names


def test_one_structural_surface_per_face(ifc):
    faces = collections.Counter(
        ifcopenshell.util.element.get_psets(member)["EPset_Topology"]["FaceIndex"]
        for member in ifc.by_type("IfcStructuralSurfaceMember")
    )
    assert faces
    assert max(faces.values()) == 1


def test_surfaces_only_for_load_bearing_types(ifc):
    """'exterior-empty' walls only hold windows, the sheathing braces the studs"""
    names = collections.Counter(
        member.Name for member in ifc.by_type("IfcStructuralSurfaceMember")
    )
    assert "framing/exterior-empty" not in names
    assert names["framing/ply-sheathing"]
    for member in ifc.by_type("IfcStructuralSurfaceMember"):
        material = ifcopenshell.util.element.get_material(member)
        if member.Name == "framing/ply-sheathing":
            assert (material.Name, round(member.Thickness, 3)) == ("Plywood", 0.025)
        if member.Name == "framing/living-floor":
            # the Concrete layer of the inherited 'living-floor' slab
            assert (material.Name, round(member.Thickness, 3)) == ("Concrete", 0.18)


def test_framing_can_be_analysed(framing, tmp_path):
    pytest.importorskip("ifc_structural_mechanics")
    if not shutil.which("ccx"):
        pytest.skip("CalculiX is not installed")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ifc_structural_mechanics.cli import cli; cli()",
            "analyze",
            str(framing),
            "--output",
            str(tmp_path / "output"),
            "--mesh-size",
            "0.5",
        ],
        capture_output=True,
        text=True,
    )
    assert "Status: success" in result.stdout, result.stdout + result.stderr
