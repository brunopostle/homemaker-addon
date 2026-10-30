"""Tests for the structural analysis model of a generated building."""

import json
import os
import subprocess
import sys

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import molior.ifc

# two rooms over two rooms, this gets windows and an entrance door
DOCUMENT = {
    "format": "homemaker-rooms",
    "version": 1,
    "name": "structural test",
    "rooms": [
        {
            "vertices": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "living",
        },
        {
            "vertices": [[5, 0], [9, 0], [9, 4], [5, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "kitchen",
        },
        {
            "vertices": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "elevation": 3.0,
            "height": 3.0,
            "usage": "bedroom",
        },
        {
            "vertices": [[5, 0], [9, 0], [9, 4], [5, 4]],
            "elevation": 3.0,
            "height": 3.0,
            "usage": "bedroom",
        },
    ],
}


@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    path = tmp_path_factory.mktemp("structural")
    rooms_path = path / "test.rooms.json"
    ifc_path = path / "test.ifc"
    rooms_path.write_text(json.dumps(DOCUMENT))
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "rooms2ifc.py"),
            str(rooms_path),
            str(ifc_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return ifcopenshell.open(str(ifc_path))


def test_materials_have_stiffness(ifc):
    """an analysis has to be told the stiffness of every structural member"""
    members = ifc.by_type("IfcStructuralMember")
    assert members
    names = set()
    for member in members:
        for material in ifcopenshell.util.element.get_materials(member):
            names.add(material.Name)
            psets = ifcopenshell.util.element.get_psets(material)
            mechanical = psets["Pset_MaterialMechanical"]
            assert 1e9 < mechanical["YoungModulus"] < 1e11
            assert 0.0 < mechanical["PoissonRatio"] < 0.5
            assert psets["Pset_MaterialCommon"]["MassDensity"] > 0.0
    assert names == {"Concrete", "Masonry"}


def test_units_of_stiffness_and_density(ifc):
    """values in share/library.ifc are Pa and kg/m3, while forces are in kN"""
    assert ifcopenshell.util.unit.calculate_unit_scale(ifc, "FORCEUNIT") == 1000.0
    assert ifcopenshell.util.unit.calculate_unit_scale(ifc, "PRESSUREUNIT") == 1.0
    assert ifcopenshell.util.unit.get_project_unit(ifc, "PRESSUREUNIT").Name == "PASCAL"
    modulus = ifcopenshell.util.unit.get_project_unit(ifc, "MODULUSOFELASTICITYUNIT")
    assert [(element.Unit.Name, element.Exponent) for element in modulus.Elements] == [
        ("PASCAL", 1)
    ]
    density = ifcopenshell.util.unit.get_project_unit(ifc, "MASSDENSITYUNIT")
    assert {
        (element.Unit.UnitType, element.Unit.Prefix, element.Exponent)
        for element in density.Elements
    } == {("MASSUNIT", "KILO", 1), ("LENGTHUNIT", None, -3)}


def test_dead_load_case(ifc):
    """the model is loaded by its own weight, with nothing else to ask for"""
    model = ifc.by_type("IfcStructuralAnalysisModel")[0]
    assert len(ifc.by_type("IfcStructuralLoadGroup")) == 1
    assert len(model.LoadedBy) == 1
    load_case = model.LoadedBy[0]
    assert load_case.is_a("IfcStructuralLoadCase")
    assert load_case.PredefinedType == "LOAD_CASE"
    assert load_case.ActionType == "PERMANENT_G"
    assert load_case.ActionSource == "DEAD_LOAD_G"
    assert load_case.SelfWeightCoefficients == (0.0, 0.0, -1.0)


def test_load_case_deleted_with_model():
    """regenerating a building has to leave one dead load, not accumulate them"""
    ifc = molior.ifc.init(name="Our Project")
    project = ifc.by_type("IfcProject")[0]
    site = molior.ifc.get_site_by_name(ifc, project, "Our Site")
    building = molior.ifc.get_building_by_name(ifc, site, "Our Building")
    model = molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours")
    assert (
        molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours") == model
    )
    assert len(ifc.by_type("IfcStructuralLoadCase")) == 1
    molior.ifc.delete_ifc_product(ifc, model)
    assert not ifc.by_type("IfcStructuralLoadCase")
    molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours")
    assert len(ifc.by_type("IfcStructuralLoadCase")) == 1


def wall_faces(ifc):
    """structural surface members of walls, with the wall they stand for"""
    for member in ifc.by_type("IfcStructuralSurfaceMember"):
        for rel in member.ReferencedBy:
            for wall in rel.RelatedObjects:
                if wall.is_a("IfcWall"):
                    yield member.Representation.Representations[0].Items[0], wall


def loop_coordinates(bound):
    return [
        edge.EdgeElement.EdgeStart.VertexGeometry.Coordinates
        for edge in bound.Bound.EdgeList
    ]


def test_walls_have_openings_in_structural_faces(ifc):
    """every window and door is a hole that stops short of the edge of the face"""
    holes = 0
    doors = 0
    for face, wall in wall_faces(ifc):
        assert face.Bounds[0].is_a("IfcFaceOuterBound")
        assert not any(bound.is_a("IfcFaceOuterBound") for bound in face.Bounds[1:])
        fillings = [
            filling.RelatedBuildingElement
            for opening in wall.HasOpenings
            for filling in opening.RelatedOpeningElement.HasFillings
        ]
        assert len(face.Bounds) - 1 == len(fillings)
        holes += len(face.Bounds) - 1
        doors += len([filling for filling in fillings if filling.is_a("IfcDoor")])

        outer = loop_coordinates(face.Bounds[0])
        assert len(outer) == 4
        floor = min(point[2] for point in outer)
        top = max(point[2] for point in outer)
        for bound in face.Bounds[1:]:
            for point in loop_coordinates(bound):
                assert floor + 0.2 - 1e-6 <= point[2] <= top - 0.2 + 1e-6
    assert holes == len(ifc.by_type("IfcWindow")) + len(ifc.by_type("IfcDoor"))
    assert holes
    assert doors


def test_structural_connections_on_faces(ifc):
    """each end of a line connection is on the outer bound of the faces it joins"""
    for rel in ifc.by_type("IfcRelConnectsStructuralMember"):
        connection = rel.RelatedStructuralConnection
        member = rel.RelatingStructuralMember
        if not connection.is_a("IfcStructuralCurveConnection"):
            continue
        if not member.is_a("IfcStructuralSurfaceMember"):
            continue
        edge = connection.Representation.Representations[0].Items[0]
        ends = [
            np.array(edge.EdgeStart.VertexGeometry.Coordinates),
            np.array(edge.EdgeEnd.VertexGeometry.Coordinates),
        ]
        face = member.Representation.Representations[0].Items[0]
        outer = [np.array(point) for point in loop_coordinates(face.Bounds[0])]
        for end in ends:
            assert any(
                np.linalg.norm(np.cross(end - outer[i - 1], outer[i] - outer[i - 1]))
                < 1e-6
                for i in range(len(outer))
            )


def test_structural_faces_keep_their_plane(ifc):
    """cutting openings doesn't move any corner out of the wall"""
    for face, _ in wall_faces(ifc):
        origin = face.FaceSurface.Position.Location.Coordinates
        normal = face.FaceSurface.Position.Axis.DirectionRatios
        for bound in face.Bounds:
            for point in loop_coordinates(bound):
                assert (
                    abs(sum((point[i] - origin[i]) * normal[i] for i in range(3)))
                    < 1e-6
                )


def test_structural_face_area(ifc):
    """the cut face is what's left of the wall, as read by a geometry kernel"""
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    for member in ifc.by_type("IfcStructuralSurfaceMember"):
        face = member.Representation.Representations[0].Items[0]

        def area(points):
            origin = np.array(points[0])
            total = np.zeros(3)
            for i in range(1, len(points) - 1):
                total += np.cross(
                    np.array(points[i]) - origin, np.array(points[i + 1]) - origin
                )
            return np.linalg.norm(total) / 2

        expected = area(loop_coordinates(face.Bounds[0])) - sum(
            area(loop_coordinates(bound)) for bound in face.Bounds[1:]
        )
        shape = ifcopenshell.geom.create_shape(settings, member).geometry
        verts = np.array(shape.verts).reshape(-1, 3)
        triangles = np.array(shape.faces).reshape(-1, 3)
        actual = sum(
            np.linalg.norm(np.cross(verts[b] - verts[a], verts[c] - verts[a])) / 2
            for a, b, c in triangles
        )
        assert actual == pytest.approx(expected)


def test_masonry_is_hinged_where_it_meets_a_slab(ifc):
    """about the line of a joint, walls rotate freely and slabs and beams stay rigid"""
    hinged = 0
    for connection in ifc.by_type("IfcStructuralCurveConnection"):
        edge = connection.Representation.Representations[0].Items[0]
        start = np.array(edge.EdgeStart.VertexGeometry.Coordinates)
        end = np.array(edge.EdgeEnd.VertexGeometry.Coordinates)
        rels = connection.ConnectsStructuralMembers
        walls = [
            rel
            for rel in rels
            if rel.RelatingStructuralMember.Name.split("/")[-1]
            in ("exterior", "interior")
        ]
        for rel in rels:
            if (
                connection.Name == "Vertical connection"
                or rel not in walls
                or len(walls) == len(rels)
            ):
                assert rel.AppliedCondition is None
                continue
            condition = rel.AppliedCondition
            assert condition.RotationalStiffnessByLengthX.wrappedValue is False
            assert condition.RotationalStiffnessByLengthY.wrappedValue is True
            assert condition.RotationalStiffnessByLengthZ.wrappedValue is True
            assert condition.TranslationalStiffnessByLengthX.wrappedValue is True
            assert condition.TranslationalStiffnessByLengthY.wrappedValue is True
            assert condition.TranslationalStiffnessByLengthZ.wrappedValue is True
            line = rel.ConditionCoordinateSystem.RefDirection.DirectionRatios
            assert np.linalg.norm(np.cross(line, end - start)) < 1e-6
            hinged += 1
    assert hinged


def test_stacked_columns_share_a_point_connection(tmp_path):
    """Columns around an outside space, one above the other"""

    def room(x, y, depth, elevation, usage):
        return {
            "vertices": [[x, y], [x + 4, y], [x + 4, y + depth], [x, y + depth]],
            "elevation": elevation,
            "height": 3.0,
            "usage": usage,
        }

    rooms = []
    for elevation in (0.0, 3.0):
        for x in (0.0, 4.0):
            rooms.append(room(x, 0.0, 4.0, elevation, "living"))
            rooms.append(room(x, 4.0, 2.0, elevation, "outside"))
    document_path = tmp_path / "porch.json"
    document_path.write_text(json.dumps({"rooms": rooms}))
    ifc_path = tmp_path / "porch.ifc"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "rooms2ifc.py"), document_path, ifc_path],
        check=True,
    )
    ifc_file = ifcopenshell.open(ifc_path)
    connections = ifc_file.by_type("IfcStructuralPointConnection")

    points = [
        tuple(
            round(coordinate, 3)
            for coordinate in connection.Representation.Representations[0]
            .Items[0]
            .VertexGeometry.Coordinates
        )
        for connection in connections
    ]
    assert connections
    assert len(points) == len(set(points))

    def columns(connection):
        result = []
        for rel in connection.ConnectsStructuralMembers:
            member = rel.RelatingStructuralMember
            if member.is_a("IfcStructuralCurveMember"):
                edge = member.Representation.Representations[0].Items[0]
                if (
                    abs(
                        edge.EdgeStart.VertexGeometry.Coordinates[2]
                        - edge.EdgeEnd.VertexGeometry.Coordinates[2]
                    )
                    > 0.001
                ):
                    result.append(member)
        return result

    at_first_floor = [
        connection
        for connection, point in zip(connections, points)
        if abs(point[2] - 3.0) < 0.001
    ]
    assert at_first_floor
    for connection in at_first_floor:
        assert len(columns(connection)) == 2
        assert connection.Name == "Column connection"
