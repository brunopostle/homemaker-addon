"""Lite mode structure: a mesh with no Cells is connected, and can be analysed."""

import collections
import json
import math
import os
import shutil
import subprocess
import sys

import pytest
from topologic_core import Face, Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from molior.rooms import document_to_faces_and_widgets


def face(vertices):
    result = Face.ByVertices([Vertex.ByCoordinates(*vertex) for vertex in vertices])
    result.Set("stylename", "default")
    return result


def ring(radius, z, degrees):
    angle = math.radians(degrees)
    return [radius * math.cos(angle), radius * math.sin(angle), z]


def cone(segments=4, rings=2):
    """Part of a cone frustum in planar quads, a developable mesh"""
    faces = []
    for segment in range(segments):
        a = 270.0 * segment / segments
        b = 270.0 * (segment + 1) / segments
        for level in range(rings):
            z0 = 5.0 * level / rings
            z1 = 5.0 * (level + 1) / rings
            r0 = 4.0 - z0 / 2.0
            r1 = 4.0 - z1 / 2.0
            faces.append(
                face(
                    [ring(r0, z0, a), ring(r0, z0, b), ring(r1, z1, b), ring(r1, z1, a)]
                )
            )
    return faces


def build(faces):
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=[])
    molior_object.execute()
    assert molior_object.cellcomplex is None
    return molior_object


def elevations(connection):
    edge = connection.Representation.Representations[0].Items[0]
    return (
        round(edge.EdgeStart.VertexGeometry.Coordinates[2], 3),
        round(edge.EdgeEnd.VertexGeometry.Coordinates[2], 3),
    )


def by_condition(molior_object):
    result = collections.defaultdict(list)
    for connection in molior_object.file.by_type("IfcStructuralCurveConnection"):
        condition = connection.AppliedCondition
        result[condition.Name if condition else None].append(connection)
    return result


def test_plates_are_connected_along_shared_edges():
    molior_object = build(cone())
    connections = molior_object.file.by_type("IfcStructuralCurveConnection")
    # 4 x 2 quads, 10 edges between them, 12 free edges: 4 + 4 on the rings, 2 x 2 ends
    members = collections.Counter(
        len(item.ConnectsStructuralMembers) for item in connections
    )
    assert members == {2: 10, 1: 12}


def test_lowest_edges_are_anchored():
    molior_object = build(cone())
    anchors = by_condition(molior_object)["Anchor"]
    assert len(anchors) == 4
    assert all(elevations(item) == (0.0, 0.0) for item in anchors)
    condition = anchors[0].AppliedCondition
    for name in ("Translational", "Rotational"):
        for axis in "XYZ":
            value = getattr(condition, f"{name}StiffnessByLength{axis}")
            assert value.wrappedValue is True


def test_free_edges_remain_as_places_to_put_a_support():
    molior_object = build(cone())
    free = [
        item
        for item in molior_object.file.by_type("IfcStructuralCurveConnection")
        if len(item.ConnectsStructuralMembers) == 1 and not item.AppliedCondition
    ]
    assert any(elevations(item) == (5.0, 5.0) for item in free)


def test_mesh_standing_on_a_corner_is_anchored_there():
    faces = [face([[0, 0, 0], [4, 0, 2], [4, 4, 4], [0, 4, 2]])]
    molior_object = build(faces)
    anchors = by_condition(molior_object)["Anchor"]
    assert len(anchors) == 2
    assert all(0.0 in elevations(item) for item in anchors)


def test_a_footing_is_not_anchored_as_well():
    room = {
        "vertices": [[0, 0], [4, 0], [4, 4], [0, 4]],
        "elevation": 0.0,
        "height": 3.0,
        "usage": "living",
    }
    apart = dict(room, vertices=[[10, 0], [14, 0], [14, 4], [10, 4]])
    faces = document_to_faces_and_widgets({"rooms": [room, apart]})[0]
    conditions = by_condition(build(faces))
    assert conditions["foundation"]
    assert not conditions["Anchor"]


def test_a_cellcomplex_is_not_anchored():
    room = {
        "vertices": [[0, 0], [4, 0], [4, 4], [0, 4]],
        "elevation": 0.0,
        "height": 3.0,
        "usage": "living",
    }
    faces, widgets = document_to_faces_and_widgets({"rooms": [room]})
    molior_object = Molior.from_faces_and_widgets(faces=faces, widgets=widgets)
    molior_object.execute()
    conditions = by_condition(molior_object)
    assert not conditions["Anchor"]
    assert all(
        len(item.ConnectsStructuralMembers) > 1
        for items in conditions.values()
        for item in items
    )


def test_analysis_balances_the_weight_of_the_mesh(tmp_path):
    pytest.importorskip("ifc_structural_mechanics")
    if not shutil.which("ccx"):
        pytest.skip("CalculiX is not installed")
    molior_object = build(cone())
    path = tmp_path / "cone.ifc"
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
            "1.0",
        ],
        capture_output=True,
        text=True,
    )
    assert "Status: success" in result.stdout, result.stdout + result.stderr
    results = json.loads((tmp_path / "output" / "results.json").read_text())
    reactions = results["global_reactions"]["by_load_case"]["Dead load"]
    assert reactions["fz_N"] > 0.0
    assert abs(reactions["imbalance_N"]) < 0.001 * reactions["fz_N"]
