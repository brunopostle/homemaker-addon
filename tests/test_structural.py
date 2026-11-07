"""Tests for the structural analysis model of a generated building."""

import json
import os
import shutil
import subprocess
import sys

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.guid
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


LINEAR_TYPES = (
    "IfcBeamType",
    "IfcColumnType",
    "IfcFootingType",
    "IfcMemberType",
    "IfcPileType",
)


def test_linear_types_have_stiffness():
    """a beam, column or member is analysed as its own material, if it has a
    stiffness, a Type in any library without one would be analysed as Concrete"""
    import glob

    checked = 0
    for path in glob.glob(
        os.path.join(ROOT, "share", "**", "library.ifc"), recursive=True
    ):
        library = ifcopenshell.open(path)
        for type_product in library.by_type("IfcTypeProduct"):
            if type_product.is_a() not in LINEAR_TYPES:
                continue
            if not molior.ifc.is_load_bearing(type_product):
                continue
            # FIXME cinema seating rows are carpet
            if type_product.Name == "Cinema row":
                continue
            for material in ifcopenshell.util.element.get_materials(type_product):
                psets = ifcopenshell.util.element.get_psets(material)
                mechanical = psets.get("Pset_MaterialMechanical", {})
                assert mechanical.get("YoungModulus"), (path, material.Name)
                assert 0.0 < mechanical["PoissonRatio"] < 0.5
                assert psets["Pset_MaterialCommon"]["MassDensity"] > 0.0
                checked += 1
    assert checked > 10


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


def test_load_cases(ifc):
    """the model is loaded by its own weight, by the use of floors and roofs,
    and by snow"""
    model = ifc.by_type("IfcStructuralAnalysisModel")[0]
    assert len(ifc.by_type("IfcStructuralLoadGroup")) == 8
    assert [group.Name for group in model.LoadedBy] == [
        "Dead load",
        "Imposed load",
        "Roof imposed load",
        "Snow load",
        "ULS",
        "ULS snow",
        "SLS",
        "SLS snow",
    ]
    dead_load, imposed_load, roof_load, snow_load = model.LoadedBy[0:4]
    for load_case in dead_load, imposed_load, roof_load, snow_load:
        assert load_case.is_a("IfcStructuralLoadCase")
        assert load_case.PredefinedType == "LOAD_CASE"
    assert dead_load.ActionType == "PERMANENT_G"
    assert dead_load.ActionSource == "DEAD_LOAD_G"
    assert dead_load.SelfWeightCoefficients == (0.0, 0.0, -1.0)
    for load_case in imposed_load, roof_load, snow_load:
        assert load_case.ActionType == "VARIABLE_Q"
        assert not load_case.SelfWeightCoefficients
    assert imposed_load.ActionSource == "LIVE_LOAD_Q"
    assert roof_load.ActionSource == "LIVE_LOAD_Q"
    assert snow_load.ActionSource == "SNOW_S"


def test_load_combinations(ifc):
    """imposed load on a roof isn't combined with snow, floors accompany snow"""
    model = ifc.by_type("IfcStructuralAnalysisModel")[0]
    factors = {
        group.Name: {
            load_case.Name: rel.Factor
            for rel in group.IsGroupedBy
            for load_case in rel.RelatedObjects
        }
        for group in model.LoadedBy[4:]
    }
    assert factors == {
        "ULS": {"Dead load": 1.35, "Imposed load": 1.5, "Roof imposed load": 1.5},
        "ULS snow": {"Dead load": 1.35, "Imposed load": 1.05, "Snow load": 1.5},
        "SLS": {"Dead load": 1.0, "Imposed load": 1.0, "Roof imposed load": 1.0},
        "SLS snow": {"Dead load": 1.0, "Imposed load": 0.7, "Snow load": 1.0},
    }
    for group in model.LoadedBy[4:]:
        assert group.PredefinedType == "LOAD_COMBINATION"


# 0.8 times the ground snow load in zone 3 at 75 m, the default Site
FLAT_SNOW = 0.8 * (0.15 + 0.35 - 25.0 / 525.0)


def test_imposed_loads_on_floors_and_roofs(ifc):
    """1.5 kN/m² on floors of dwellings, 0.6 kN/m² on a roof without access,
    and snow on the roof"""
    loads = {}
    for action in ifc.by_type("IfcStructuralPlanarAction"):
        (rel,) = action.AssignedToStructuralItem
        (group,) = [rel.RelatingGroup for rel in action.HasAssignments]
        assert action.Name == group.Name
        assert action.GlobalOrLocal == "GLOBAL_COORDS"
        load = action.AppliedLoad
        assert not load.PlanarForceX and not load.PlanarForceY
        loads.setdefault((rel.RelatingElement.Name, group.Name), set()).add(
            round(load.PlanarForceZ, 6)
        )
    assert loads == {
        ("default/living-floor", "Imposed load"): {-1.5},
        ("default/kitchen-floor", "Imposed load"): {-1.5},
        ("default/bedroom-floor", "Imposed load"): {-1.5},
        ("default/flat-roof", "Roof imposed load"): {-0.6},
        ("default/flat-roof", "Snow load"): {round(-FLAT_SNOW, 6)},
    }


def test_imposed_load_of_a_pitched_roof():
    from molior.shell import imposed_load

    # a floor is loaded the same on plan and on its true area
    assert imposed_load("living", [0.0, 0.0, 1.0]) == 1.5
    assert imposed_load("living", [0.0, 0.0, -1.0]) == 1.5
    # nothing on walls or soffits, unless the style says so
    assert imposed_load("external", [1.0, 0.0, 0.0]) == 0.0
    assert imposed_load("soffit", [0.0, 0.0, -1.0]) == 0.0
    assert imposed_load("soffit", [0.0, 0.0, -1.0], 2.0) == 2.0
    # 0.6 kN/m² on plan up to 30°, then less to nothing at 60°
    pitch = np.radians(30.0)
    assert imposed_load("roof", [0.0, np.sin(pitch), np.cos(pitch)]) == (
        pytest.approx(0.6 * np.cos(pitch))
    )
    pitch = np.radians(45.0)
    assert imposed_load("roof", [0.0, np.sin(pitch), np.cos(pitch)]) == (
        pytest.approx(0.3 * np.cos(pitch))
    )
    pitch = np.radians(70.0)
    assert imposed_load("roof", [0.0, np.sin(pitch), np.cos(pitch)]) == 0.0


def test_snow_load():
    from molior.shell import ground_snow_load, snow_load, gravity_loads

    # UK National Annex, zone 3: 0.5 kN/m² at 100 m, more higher up
    assert ground_snow_load(100.0) == pytest.approx(0.5)
    assert ground_snow_load(625.0) == pytest.approx(1.5)
    assert ground_snow_load(100.0, zone=1) == pytest.approx(0.3)
    assert ground_snow_load(-1000.0) == 0.0
    # shape coefficient 0.8 up to 30°, then less to nothing at 60°
    assert snow_load("flat", [0.0, 0.0, 1.0], 100.0) == pytest.approx(0.4)
    pitch = np.radians(45.0)
    normal = [0.0, np.sin(pitch), np.cos(pitch)]
    assert snow_load("roof", normal, 100.0) == pytest.approx(0.2 * np.cos(pitch))
    pitch = np.radians(70.0)
    assert snow_load("roof", [0.0, np.sin(pitch), np.cos(pitch)], 100.0) == 0.0
    # no snow on floors, unless the style says so
    assert snow_load("living", [0.0, 0.0, 1.0], 100.0) == 0.0
    assert snow_load("outside", [0.0, 0.0, 1.0], 100.0, 0.5) == 0.5
    # imposed load on roofs is a case of its own
    assert gravity_loads("living", [0.0, 0.0, 1.0], 100.0) == {
        "Imposed load": 1.5,
        "Snow load": 0.0,
    }
    assert gravity_loads("roof", [0.0, 0.0, 1.0], 100.0, snow=1.0) == {
        "Roof imposed load": 0.6,
        "Snow load": 1.0,
    }


def test_snow_at_the_altitude_of_the_site():
    ifc = molior.ifc.init(name="Our Project")
    project = ifc.by_type("IfcProject")[0]
    site = molior.ifc.get_site_by_name(ifc, project, "Our Site", elevation=300.0)
    building = molior.ifc.get_building_by_name(ifc, site, "Our Building")
    model = molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours")
    assert molior.ifc.get_site_altitude(model) == 300.0
    site.RefElevation = None
    assert molior.ifc.get_site_altitude(model) == 0.0


def test_load_case_deleted_with_model():
    """regenerating a building has to leave one set of loads, not accumulate them"""
    ifc = molior.ifc.init(name="Our Project")
    project = ifc.by_type("IfcProject")[0]
    site = molior.ifc.get_site_by_name(ifc, project, "Our Site")
    building = molior.ifc.get_building_by_name(ifc, site, "Our Building")
    model = molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours")
    assert (
        molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours") == model
    )
    assert len(ifc.by_type("IfcStructuralLoadGroup")) == 8
    member = ifc.createIfcStructuralSurfaceMember(ifcopenshell.guid.new())
    molior.ifc.add_gravity_load(ifc, model, member, 1.5)
    molior.ifc.add_gravity_load(ifc, model, member, 0.4, "Snow load")
    assert not molior.ifc.add_gravity_load(ifc, model, member, 0.0)
    assert len(ifc.by_type("IfcStructuralPlanarAction")) == 2
    molior.ifc.delete_ifc_product(ifc, model)
    assert not ifc.by_type("IfcStructuralLoadGroup")
    assert not ifc.by_type("IfcStructuralPlanarAction")
    assert not ifc.by_type("IfcStructuralLoadPlanarForce")
    assert not ifc.by_type("IfcRelConnectsStructuralActivity")
    molior.ifc.get_structural_analysis_model_by_name(ifc, building, "Ours")
    assert len(ifc.by_type("IfcStructuralLoadGroup")) == 8


def wall_members(ifc):
    """structural surface members of walls, with the wall they stand for"""
    for member in ifc.by_type("IfcStructuralSurfaceMember"):
        for rel in member.ReferencedBy:
            for wall in rel.RelatedObjects:
                if wall.is_a("IfcWall"):
                    yield member, wall


def wall_faces(ifc):
    """faces of structural surface members of walls, with the wall"""
    for member, wall in wall_members(ifc):
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
    for member, wall in wall_members(ifc):
        face = member.Representation.Representations[0].Items[0]
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
                assert (
                    floor + member.Thickness - 1e-6
                    <= point[2]
                    <= top - member.Thickness + 1e-6
                )
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


@pytest.fixture(scope="module")
def porch(tmp_path_factory):
    """Two storeys of rooms with columns and beams around an outside space"""

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
    path = tmp_path_factory.mktemp("porch")
    document_path = path / "porch.json"
    document_path.write_text(json.dumps({"rooms": rooms}))
    ifc_path = path / "porch.ifc"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "rooms2ifc.py"), document_path, ifc_path],
        check=True,
    )
    return ifcopenshell.open(ifc_path)


def member_ends(member):
    edge = member.Representation.Representations[0].Items[0]
    return [
        tuple(round(coordinate, 3) for coordinate in vertex.VertexGeometry.Coordinates)
        for vertex in (edge.EdgeStart, edge.EdgeEnd)
    ]


def connection_point(connection):
    return tuple(
        round(coordinate, 3)
        for coordinate in connection.Representation.Representations[0]
        .Items[0]
        .VertexGeometry.Coordinates
    )


def test_point_connections_are_not_coincident(porch):
    points = [
        connection_point(connection)
        for connection in porch.by_type("IfcStructuralPointConnection")
    ]
    assert points
    assert len(points) == len(set(points))


def test_stacked_columns_share_a_point_connection(porch):
    at_first_floor = [
        connection
        for connection in porch.by_type("IfcStructuralPointConnection")
        if connection_point(connection)[2] == 3.0
        and connection.Name.startswith("Column")
    ]
    assert at_first_floor
    for connection in at_first_floor:
        columns = []
        for rel in connection.ConnectsStructuralMembers:
            member = rel.RelatingStructuralMember
            if member.is_a("IfcStructuralCurveMember"):
                start, end = member_ends(member)
                if start[2] != end[2]:
                    columns.append(member)
        assert len(columns) == 2
        assert connection.Name == "Column connection"


def test_horizontal_members_are_connected_where_they_meet(porch):
    connections = {}
    for connection in porch.by_type("IfcStructuralPointConnection"):
        connections[connection_point(connection)] = {
            rel.RelatingStructuralMember for rel in connection.ConnectsStructuralMembers
        }

    at_point = {}
    for member in porch.by_type("IfcStructuralCurveMember"):
        start, end = member_ends(member)
        if start[2] == end[2]:
            for point in (start, end):
                at_point.setdefault(point, []).append(member)

    meeting = {
        point: members for point, members in at_point.items() if len(members) > 1
    }
    assert meeting
    for point, members in meeting.items():
        assert connections[point].issuperset(members)


def test_columns_and_beams_are_timber(porch):
    """the default Types are timber, they aren't analysed as concrete"""
    for element_class, name in (("IfcColumn", "Wood"), ("IfcBeam", "Timber")):
        elements = porch.by_type(element_class)
        assert elements
        for element in elements:
            members = [
                rel.RelatingProduct
                for rel in element.HasAssignments
                if rel.is_a("IfcRelAssignsToProduct")
                and rel.RelatingProduct.is_a("IfcStructuralCurveMember")
            ]
            assert members, element
            for member in members:
                materials = ifcopenshell.util.element.get_materials(member)
                assert [material.Name for material in materials] == [name]


def test_columns_have_an_axis_the_height_of_their_body(porch):
    settings = ifcopenshell.geom.settings()
    columns = porch.by_type("IfcColumn")
    assert columns
    for column in columns:
        axes = [
            representation
            for representation in column.Representation.Representations
            if representation.RepresentationIdentifier == "Axis"
        ]
        assert len(axes) == 1
        axis = axes[0].Items[0].MappingSource.MappedRepresentation
        start, end = axis.Items[0].Points.CoordList
        assert start == (0.0, 0.0, 0.0)
        shape = ifcopenshell.geom.create_shape(settings, column)
        heights = np.array(shape.geometry.verts).reshape(-1, 3)[:, 2]
        assert end == pytest.approx((0.0, 0.0, heights.max()), abs=1e-6)
        assert heights.min() == pytest.approx(0.0, abs=1e-6)


def test_imposed_load_is_carried(ifc, tmp_path):
    """72 m² of floor at 1.5 kN/m², 36 m² of flat roof at 0.6 kN/m², and snow"""
    pytest.importorskip("ifc_structural_mechanics")
    if not shutil.which("ccx"):
        pytest.skip("CalculiX is not installed")
    path = tmp_path / "test.ifc"
    ifc.write(str(path))
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
    reactions = results["global_reactions"]
    by_load_case = reactions["by_load_case"]
    imposed = by_load_case["Imposed load"]["fz_N"]
    assert imposed == pytest.approx(1000.0 * 72 * 1.5, rel=0.001)
    roof = by_load_case["Roof imposed load"]["fz_N"]
    assert roof == pytest.approx(1000.0 * 36 * 0.6, rel=0.001)
    snow = by_load_case["Snow load"]["fz_N"]
    assert snow == pytest.approx(1000.0 * 36 * FLAT_SNOW, rel=0.001)
    dead = by_load_case["Dead load"]["fz_N"]
    by_combination = reactions["by_load_combination"]
    uls = by_combination["ULS"]["fz_N"]
    assert uls == pytest.approx(1.35 * dead + 1.5 * (imposed + roof), rel=0.001)
    uls = by_combination["ULS snow"]["fz_N"]
    assert uls == pytest.approx(1.35 * dead + 1.05 * imposed + 1.5 * snow, rel=0.001)
