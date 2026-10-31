"""The 'plate' style makes every Face a plate that can be analysed."""

import collections
import json
import os
import shutil
import subprocess
import sys

import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np
import pytest
from topologic_core import Face, Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior

# inclined, a vertical wall, and a triangle that is vertical with no bottom edge
SLOPE = [[0, 0, 0], [4, 0, 0], [4, 3, 4], [0, 3, 4]]
WALL = [[4, 0, 0], [8, 0, 0], [8, 0, 3], [4, 0, 3]]
SIDE = [[4, 0, 0], [4, 3, 4], [4, 0, 3]]
BOX = [
    [[0, 0, 0], [0, 4, 0], [4, 4, 0], [4, 0, 0]],
    [[0, 0, 3], [4, 0, 3], [4, 4, 3], [0, 4, 3]],
    [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]],
    [[4, 0, 0], [4, 4, 0], [4, 4, 3], [4, 0, 3]],
    [[4, 4, 0], [0, 4, 0], [0, 4, 3], [4, 4, 3]],
    [[0, 4, 0], [0, 0, 0], [0, 0, 3], [0, 4, 3]],
]


def build(items):
    faces = []
    for vertices in items:
        face = Face.ByVertices([Vertex.ByCoordinates(*item) for item in vertices])
        face.Set("stylename", "plate")
        faces.append(face)
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    molior_object.execute()
    return molior_object


def physical(molior_object):
    return collections.Counter(
        item.is_a()
        for item in molior_object.file.by_type("IfcElement")
        if not item.is_a("IfcElementAssembly")
    )


@pytest.mark.parametrize(
    "items,plates",
    [([SLOPE, WALL, SIDE], 3), (BOX, 6)],
    ids=["open mesh", "closed mesh"],
)
def test_every_face_is_a_plate_and_nothing_else(items, plates):
    assert physical(build(items)) == {"IfcPlate": plates}


def test_plates_are_typed_with_a_layer_of_steel():
    molior_object = build([SLOPE])
    plate = molior_object.file.by_type("IfcPlate")[0]
    plate_type = ifcopenshell.util.element.get_type(plate)
    assert plate_type.is_a("IfcPlateType")
    layer_set = ifcopenshell.util.element.get_material(plate_type)
    assert layer_set.MaterialLayers[0].LayerThickness == pytest.approx(0.01)


def test_structural_members_are_the_same_as_the_plates():
    molior_object = build([SLOPE, WALL, SIDE])
    members = molior_object.file.by_type("IfcStructuralSurfaceMember")
    assert len(members) == 3
    for member in members:
        assert member.Thickness == pytest.approx(0.01)
        material = ifcopenshell.util.element.get_material(member)
        assert material.Name == "Steel plate"
        psets = ifcopenshell.util.element.get_psets(material)
        assert psets["Pset_MaterialCommon"]["MassDensity"] == pytest.approx(7850.0)
        assert psets["Pset_MaterialMechanical"]["YoungModulus"] > 0.0


@pytest.mark.parametrize(
    "vertices", [SLOPE, WALL, SIDE], ids=["inclined", "vertical", "triangle"]
)
def test_plates_are_centred_on_the_face(vertices):
    molior_object = build([vertices])
    plate = molior_object.file.by_type("IfcPlate")[0]
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, plate)
    points = np.array(shape.geometry.verts).reshape(-1, 3)
    corners = np.array(vertices, dtype=float)
    normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
    normal /= np.linalg.norm(normal)
    distances = (points - corners[0]) @ normal
    # an inclined extrusion is thickness measured square to the face
    assert distances.max() == pytest.approx(0.005, abs=0.0001)
    assert distances.min() == pytest.approx(-0.005, abs=0.0001)


def test_closed_mesh_is_anchored():
    molior_object = build(BOX)
    assert molior_object.cellcomplex is not None
    anchors = [
        item
        for item in molior_object.file.by_type("IfcStructuralCurveConnection")
        if item.AppliedCondition
    ]
    assert len(anchors) == 4
    assert {item.AppliedCondition.Name for item in anchors} == {"Anchor"}


def test_each_mesh_in_a_file_is_anchored():
    first = build([SLOPE])
    face = Face.ByVertices(
        [Vertex.ByCoordinates(x + 20.0, y, z + 1.0) for x, y, z in SLOPE]
    )
    face.Set("stylename", "plate")
    second = Molior.from_faces_and_widgets(
        file=first.file, faces=[face], widgets=[], name="second"
    )
    second.execute()
    anchors = [
        item
        for item in first.file.by_type("IfcStructuralCurveConnection")
        if item.AppliedCondition
    ]
    assert len(anchors) == 2


def test_analysis_balances_the_weight_of_the_steel(tmp_path):
    pytest.importorskip("ifc_structural_mechanics")
    if not shutil.which("ccx"):
        pytest.skip("CalculiX is not installed")
    molior_object = build([SLOPE, WALL, SIDE])
    path = tmp_path / "plate.ifc"
    molior_object.file.write(str(path))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ifc_structural_mechanics.cli import cli; cli()",
            "analyze",
            str(path),
            "--output",
            str(tmp_path / "output"),
            "--mesh-size",
            "0.5",
        ],
        capture_output=True,
        text=True,
    )
    assert "Status: success" in result.stdout, result.stdout + result.stderr
    results = json.loads((tmp_path / "output" / "results.json").read_text())
    reactions = results["global_reactions"]["by_load_case"]["Dead load"]
    area = 4.0 * 5.0 + 4.0 * 3.0 + 4.5
    weight = area * 0.01 * 7850.0 * 9.81
    assert reactions["fz_N"] == pytest.approx(weight, rel=0.001)
