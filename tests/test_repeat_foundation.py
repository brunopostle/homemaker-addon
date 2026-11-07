"""Piles and pad footings placed by a Repeat are structural members, supported
at their base, instead of the strip foundation of a ground beam."""

import os
import shutil
import sys

import pytest
from topologic_core import Face, Vertex

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from molior import Molior

TRACES = """---
ground beam:
  ifc: IfcBeam
internal ground beam:
  condition: noop
pile:
  class: Repeat
  ifc: {ifc}
  family: pile
  condition: bottom-backward-level
  offset: 0.0
  yshift: -{depth}
  spacing: 2.0
  structural_material: Concrete
  structural_profile:
    - IfcCircleProfileDef
    - ProfileType: AREA
      Radius: 0.15
"""

FAMILIES = """---
pile:
  -
    typename: pile
    height: {depth}
"""


def box(stylename):
    """A single room, 4m square and 3m high"""
    corners = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
    faces = []
    for z in (0.0, 3.0):
        faces.append([[*corner, z] for corner in corners])
    for index in range(4):
        a = corners[index]
        b = corners[(index + 1) % 4]
        faces.append([[*a, 0.0], [*b, 0.0], [*b, 3.0], [*a, 3.0]])
    result = []
    for vertices in faces:
        face = Face.ByVertices([Vertex.ByCoordinates(*vertex) for vertex in vertices])
        face.Set("stylename", stylename)
        result.append(face)
    return result


def build(tmp_path, ifc, depth):
    share_dir = tmp_path / "share"
    shutil.copytree(os.path.join(ROOT, "share"), share_dir)
    (share_dir / "piled").mkdir()
    (share_dir / "piled" / "traces.yml").write_text(TRACES.format(ifc=ifc, depth=depth))
    (share_dir / "piled" / "families.yml").write_text(FAMILIES.format(depth=depth))
    molior_object = Molior.from_faces_and_widgets(
        faces=box("piled"), widgets=[], share_dir=str(share_dir)
    )
    molior_object.execute()
    return molior_object.file


def ends(member):
    edge = member.Representation.Representations[0].Items[0]
    return [
        tuple(round(coordinate, 3) for coordinate in vertex.VertexGeometry.Coordinates)
        for vertex in (edge.EdgeStart, edge.EdgeEnd)
    ]


def point(connection):
    return tuple(
        round(coordinate, 3)
        for coordinate in connection.Representation.Representations[0]
        .Items[0]
        .VertexGeometry.Coordinates
    )


@pytest.mark.parametrize("ifc_class,depth", [("IfcPile", 6.0), ("IfcFooting", 0.5)])
def test_foundation_is_a_supported_member(tmp_path, ifc_class, depth):
    ifc = build(tmp_path, ifc_class, depth)
    elements = ifc.by_type(ifc_class)
    assert elements
    members = []
    for member in ifc.by_type("IfcStructuralCurveMember"):
        products = [
            related
            for referenced_by in member.ReferencedBy
            for related in referenced_by.RelatedObjects
        ]
        if any(product.is_a(ifc_class) for product in products):
            members.append(member)
    assert len(members) == len(elements)

    for member in members:
        base, head = sorted(ends(member), key=lambda coors: coors[2])
        assert base[0:2] == head[0:2]
        assert base[2] == -depth
        assert head[2] == 0.0
        connections = {
            point(rel.RelatedStructuralConnection): rel.RelatedStructuralConnection
            for rel in member.ConnectedBy
            if rel.RelatedStructuralConnection.is_a("IfcStructuralPointConnection")
        }
        # the base is pinned
        support = connections[base]
        condition = support.AppliedCondition
        assert condition.is_a("IfcBoundaryNodeCondition")
        assert condition.TranslationalStiffnessX.wrappedValue is True
        assert condition.TranslationalStiffnessY.wrappedValue is True
        assert condition.TranslationalStiffnessZ.wrappedValue is True
        assert condition.RotationalStiffnessX.wrappedValue is False
        # the head carries the wall and ground beam above
        carried = [
            rel.RelatingStructuralMember
            for rel in connections[head].ConnectsStructuralMembers
            if rel.RelatingStructuralMember != member
        ]
        assert carried

    # nothing else is a support, the lowest edges aren't anchored
    supported = [
        connection
        for connection in ifc.by_type("IfcStructuralConnection")
        if connection.AppliedCondition
    ]
    assert len(supported) == len(members)
