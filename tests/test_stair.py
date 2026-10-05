"""Tests for molior/stair.py, stairs that wind around the perimeter of a cell"""

import math
import os
import sys

import pytest
from shapely.geometry import LineString, Polygon

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import ifcopenshell.geom  # noqa: E402
import ifcopenshell.util.element  # noqa: E402
import ifcopenshell.util.placement  # noqa: E402
from molior import Molior  # noqa: E402
from molior.rooms import rooms_to_faces_and_widgets  # noqa: E402
from molior.stair import (  # noqa: E402
    ANTICLOCKWISE,
    CLOCKWISE,
    Ring,
    ideal_going,
    plan_best,
    plan_doors,
    plan_landing,
    plan_stack,
    plan_treads,
    risers_number,
    simplify_polygon,
    subtract_intervals,
)

RECTANGLE = [[0.0, 0.0], [3.0, 0.0], [3.0, 5.0], [0.0, 5.0]]


def level(polygon, doors_top, doors_bottom, treads=15):
    return {
        "polygon": polygon,
        "width": 0.92,
        "treads": treads,
        "going": 0.25,
        "doors_top": doors_top,
        "doors_bottom": doors_bottom,
    }


def area(polygon):
    return Polygon(polygon).area


# ---------------------------------------------------------------------------
# arithmetic ported from Urb::Misc::Stairs
# ---------------------------------------------------------------------------


def test_risers_number():
    assert risers_number(3.0, 0.21) == 15
    assert risers_number(3.0, 0.2) == 15
    assert risers_number(3.0, 0.19) == 16
    assert risers_number(0.1, 0.19) == 1


def test_ideal_going():
    assert ideal_going(0.2) == pytest.approx(0.225)
    assert ideal_going(0.1875) == pytest.approx(0.25)
    assert ideal_going(0.21) == pytest.approx(0.22)
    assert ideal_going(0.25) == pytest.approx(0.22)


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_simplify_polygon():
    polygon = [[0, 0], [1.5, 0], [3, 0], [3, 5], [3, 5], [0, 5]]
    assert [list(point) for point in simplify_polygon(polygon)] == RECTANGLE


def test_ring_rectangle():
    ring = Ring(RECTANGLE, 1.0)
    assert ring.perimeter == pytest.approx(16.0)
    assert ring.width == pytest.approx(1.0)
    assert [list(newel) for newel in ring.newel] == [
        pytest.approx(point) for point in ([1, 1], [2, 1], [2, 4], [1, 4])
    ]
    assert [ring.winders(index) for index in range(4)] == [3, 3, 3, 3]
    # kites and runs tile the strip between the walls and the well
    total = sum(area(ring.polygon_kite(index)) for index in range(4))
    for piece in ring.pieces:
        if piece["kind"] == "run":
            total += area(ring.polygon_run(piece["index"], piece["lo"], piece["hi"]))
    assert total == pytest.approx(15.0 - area(ring.polygon_well()))
    # winders tile a kite
    winders = ring.polygons_winders(2, 3)
    assert len(winders) == 3
    assert sum(area(winder) for winder in winders) == pytest.approx(1.0)


def test_ring_stations():
    ring = Ring(RECTANGLE, 1.0)
    assert ring.station([1.5, -0.3]) == pytest.approx(1.5)
    assert ring.station([3.2, 2.0]) == pytest.approx(5.0)
    assert list(ring.point_outer(5.0)) == pytest.approx([3.0, 2.0])
    assert list(ring.point_outer(5.0 + 16.0)) == pytest.approx([3.0, 2.0])
    assert list(ring.point_inner(5.0)) == pytest.approx([2.0, 2.0])
    # inside a kite the inner edge is the newel
    assert list(ring.point_inner(3.5)) == pytest.approx([2.0, 1.0])
    # stations inside a kite snap to either end of it
    assert ring.snap(3.5, True) == pytest.approx(4.0)
    assert ring.snap(3.5, False) == pytest.approx(2.0)
    assert ring.snap(5.0, True) == pytest.approx(5.0)


def test_ring_narrow_cell_gets_a_narrower_stair():
    ring = Ring([[0, 0], [1.6, 0], [1.6, 5], [0, 5]], 1.0)
    assert ring.width == pytest.approx(0.8)


def test_ring_any_convex_polygon():
    hexagon = [
        [3 * math.cos(math.radians(a)), 3 * math.sin(math.radians(a))]
        for a in range(0, 360, 60)
    ]
    ring = Ring(hexagon, 1.0)
    assert [ring.winders(index) for index in range(6)] == [2] * 6
    assert area(ring.polygon_well()) < area(hexagon)


def test_ring_rejects_bad_polygons():
    with pytest.raises(ValueError):
        Ring(list(reversed(RECTANGLE)), 1.0)
    with pytest.raises(ValueError):
        Ring([[0, 0], [4, 0], [4, 4], [2, 1], [0, 4]], 1.0)


def test_subtract_intervals():
    spans = subtract_intervals([[0.0, 10.0]], [[2.0, 1.0], [9.5, 1.0]], 10.0)
    assert spans == [pytest.approx(span) for span in ([0.5, 2.0], [3.0, 9.5])]


# ---------------------------------------------------------------------------
# planning
# ---------------------------------------------------------------------------


def blocked(plan, doors):
    """Does any tread sit in front of a door?"""
    ring = plan["ring"]
    for polygon, _, _ in plan_treads(plan):
        for point, half_width, _ in doors:
            if plan["rotation"] == CLOCKWISE:
                point = [-point[0], point[1]]
            station = ring.station(point)
            front = LineString(
                [
                    ring.point_outer(station - half_width + 0.01),
                    ring.point_outer(station + half_width - 0.01),
                ]
            )
            if (
                Polygon(polygon)
                .buffer(-0.01)
                .intersects(front.buffer(0.3, cap_style=2))
            ):
                return True
    return False


def test_plan_no_doors():
    plans, fit = plan_stack([level(RECTANGLE, [], [])])
    assert fit >= 1.0
    treads = plan_treads(plans[0])
    assert [tread[1] for tread in treads] == list(range(1, 16))
    # a stair with room to spare has quarter landings, not winders
    assert all(
        item["steps"] == 1 for item in plans[0]["items"] if item["kind"] == "kite"
    )


def test_plan_winders_when_tight():
    square = [[0, 0], [2.3, 0], [2.3, 2.3], [0, 2.3]]
    plans, fit = plan_stack([level(square, [], [])])
    assert fit >= 1.0
    assert any(
        item["steps"] == 3 for item in plans[0]["items"] if item["kind"] == "kite"
    )
    assert plan_treads(plans[0])[-1][1] == 15


def test_plan_avoids_doors():
    doors_top = [[[3.0, 2.5], 0.55, False]]
    doors_bottom = [[[0.0, 2.5], 0.55, False]]
    plans, fit = plan_stack([level(RECTANGLE, doors_top, doors_bottom)])
    assert fit >= 1.0
    assert not blocked(plans[0], doors_top + doors_bottom)
    assert plan_treads(plans[0])[-1][1] == 15


def test_plan_landing():
    doors = [[[3.0, 1.0], 0.55, False]]
    levels = [level(RECTANGLE, doors, doors), level(RECTANGLE, doors, doors)]
    plans, fit = plan_stack(levels)
    assert fit >= 1.0
    # the top of the stack is floored, apart from a hole for the flight
    polygons, _, _ = plan_landing(plans[0], True)
    flight = sum(area(tread[0]) for tread in plan_treads(plans[0]))
    inside = area(RECTANGLE)
    assert sum(area(polygon) for polygon in polygons) == pytest.approx(inside - flight)
    # lower down the landing runs from the flight above to the flight below
    polygons, lo, hi = plan_landing(plans[1], False)
    ring = plans[1]["ring"]
    assert list(ring.point_outer(lo)) == pytest.approx(
        list(plans[0]["ring"].point_outer(plans[0]["foot"]))
    )
    assert hi == pytest.approx(plans[1]["head"])
    assert sum(area(polygon) for polygon in polygons) < inside - flight


def test_plan_squeezed():
    # doors on every side at both floors leave too little room
    doors = [
        [[1.5, 0.0], 0.55, False],
        [[3.0, 2.5], 0.55, False],
        [[1.5, 5.0], 0.55, False],
        [[0.0, 2.5], 0.55, False],
    ]
    plans, fit = plan_stack([level(RECTANGLE, doors, doors)])
    assert 0.0 < fit < 1.0
    # ..but we still get there
    assert plan_treads(plans[0])[-1][1] == 15
    assert not blocked(plans[0], doors)


def test_plan_sacrifices_outside_doors():
    inside = [[[3.0, 2.5], 0.55, False]]
    outside = [
        [[1.5, 0.0], 0.55, True],
        [[1.5, 5.0], 0.55, True],
        [[0.0, 2.5], 0.55, True],
    ]
    plans = plan_best([level(RECTANGLE, inside, inside + outside)])
    assert plans[0]["fit"] >= 1.0
    assert not blocked(plans[0], inside)
    assert blocked(plans[0], outside)


def test_plan_rotation():
    # traditionally stairs rise clockwise
    doors = [[[3.0, 1.0], 0.55, False]]
    plans = plan_best([level(RECTANGLE, doors, doors), level(RECTANGLE, doors, doors)])
    assert [plan["rotation"] for plan in plans] == [ANTICLOCKWISE, ANTICLOCKWISE]

    # ..unless the doors only allow a stair the other way around
    floors = [
        [[[1.5, 0.0], 0.55, False]],
        [[[3.0, 4.0], 0.55, False]],
        [[[0.0, 2.5], 0.55, False]],
    ]
    levels = [
        level(RECTANGLE, floors[0], floors[1]),
        level(RECTANGLE, floors[1], floors[2]),
    ]
    assert plan_stack(levels, ANTICLOCKWISE)[1] < 1.0
    assert plan_stack(levels, CLOCKWISE)[1] >= 1.0
    plans = plan_best(levels)
    assert [plan["rotation"] for plan in plans] == [CLOCKWISE, CLOCKWISE]
    for plan, doors_top, doors_bottom in zip(plans, floors, floors[1:]):
        assert not blocked(plan, doors_top + doors_bottom)


# ---------------------------------------------------------------------------
# doors
# ---------------------------------------------------------------------------


def test_plan_doors_bunches_doors_together():
    ring = Ring(RECTANGLE, 1.0)
    faces = [
        # east and north walls each need a door
        {"key": "east", "lo": 3.25, "hi": 7.75, "optional": False},
        {"key": "north", "lo": 8.25, "hi": 10.75, "optional": False},
    ]
    places = plan_doors(ring, faces, slot=1.2)
    # either side of the corner between them
    assert places["east"] == pytest.approx(7.75 - 0.6)
    assert places["north"] == pytest.approx(8.25 + 0.6)


def test_plan_doors_one_entrance():
    ring = Ring(RECTANGLE, 1.0)
    faces = [
        {"key": "south", "lo": 0.25, "hi": 2.75, "optional": True},
        {"key": "east", "lo": 3.25, "hi": 7.75, "optional": False},
        {"key": "north", "lo": 8.25, "hi": 10.75, "optional": True},
        {"key": "west", "lo": 11.25, "hi": 15.75, "optional": True},
    ]
    places = plan_doors(ring, faces, slot=1.2)
    chosen = [key for key in ("south", "north", "west") if places[key] is not None]
    assert len(chosen) == 1
    # next to the door that is needed
    assert abs(places[chosen[0]] - places["east"]) == pytest.approx(1.7)

    # an entrance is better than nothing
    places = plan_doors(ring, faces[:1], slot=1.2)
    assert places["south"] is not None


def test_plan_doors_long_wall():
    ring = Ring(RECTANGLE, 1.0)
    faces = [
        {"key": "east", "lo": 3.25, "hi": 7.75, "optional": False},
        {"key": "west", "lo": 11.25, "hi": 15.75, "optional": False},
    ]
    places = plan_doors(ring, faces, slot=1.2)
    # opposite walls, both doors go to the same end of the cell
    east = ring.point_outer(places["east"])
    west = ring.point_outer(places["west"])
    assert east[1] == pytest.approx(west[1])


# ---------------------------------------------------------------------------
# IFC
# ---------------------------------------------------------------------------


def build(stair, other, storeys=3, degrees=0.0, stair_usage="stair"):
    cos, sin = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))

    def rotate(points):
        return [[x * cos - y * sin, x * sin + y * cos] for x, y in points]

    rooms = []
    for storey in range(storeys):
        for vertices, usage in (stair, stair_usage), (other, "living"):
            rooms.append(
                {
                    "vertices": rotate(vertices),
                    "elevation": 3.0 * storey,
                    "height": 3.0,
                    "usage": usage,
                }
            )
    faces, widgets = rooms_to_faces_and_widgets(rooms)
    molior_object = Molior.from_faces_and_widgets(
        faces=faces,
        widgets=widgets,
        name="stair test",
        share_dir=os.path.join(ROOT, "share"),
    )
    molior_object.execute()
    return molior_object.file


def extents(element):
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    verts = ifcopenshell.geom.create_shape(settings, element).geometry.verts
    return [
        [min(verts[axis::3]) for axis in range(3)],
        [max(verts[axis::3]) for axis in range(3)],
    ]


@pytest.fixture(scope="module")
def ifc():
    return build(RECTANGLE, [[3, 0], [8, 0], [8, 5], [3, 5]])


def test_stair_for_every_storey_but_the_top(ifc):
    stairs = ifc.by_type("IfcStair")
    assert len(stairs) == 2
    elevations = sorted(
        ifcopenshell.util.placement.get_local_placement(stair.ObjectPlacement)[2][3]
        for stair in stairs
    )
    assert elevations == pytest.approx([0.0, 3.0])
    for stair in stairs:
        psets = ifcopenshell.util.element.get_psets(stair)
        assert psets["Pset_StairCommon"]["NumberOfRiser"] == 16
        assert psets["Pset_StairCommon"]["NumberOfTreads"] == 15
        assert psets["Pset_StairCommon"]["RiserHeight"] == pytest.approx(0.1875)
        assert psets["Pset_StairCommon"]["TreadLength"] >= 0.25
        assert "CellIndex" in psets["EPset_Topology"]


def test_stair_parts(ifc):
    for stair in ifc.by_type("IfcStair"):
        elevation = ifcopenshell.util.placement.get_local_placement(
            stair.ObjectPlacement
        )[2][3]
        parts = {
            part.is_a(): part
            for part in ifcopenshell.util.element.get_decomposition(stair)
        }
        assert sorted(parts) == ["IfcRailing", "IfcSlab", "IfcStairFlight"]

        flight = parts["IfcStairFlight"]
        assert len(flight.Representation.Representations[0].Items) == 15
        lowest, highest = extents(flight)
        # from the floor to one riser below the floor above
        assert lowest[2] == pytest.approx(elevation, abs=0.001)
        assert highest[2] == pytest.approx(elevation + 3.0 - 0.1875, abs=0.001)
        # within the walls
        assert lowest[0] >= 0.079 and highest[0] <= 2.921
        assert lowest[1] >= 0.079 and highest[1] <= 4.921

        landing = parts["IfcSlab"]
        assert landing.PredefinedType == "LANDING"
        lowest, highest = extents(landing)
        assert highest[2] == pytest.approx(elevation + 3.0, abs=0.001)

        lowest, highest = extents(parts["IfcRailing"])
        assert highest[2] > elevation + 3.0 + 0.9


def test_one_entrance_to_a_stack_of_stair_cells(ifc):
    entrances = [
        door
        for door in ifc.by_type("IfcDoor")
        if door.Name == "house entrance"
        and ifcopenshell.util.element.get_psets(door)["EPset_Topology"]["BackCellIndex"]
        == "0"
    ]
    assert len(entrances) == 1


def test_stair_keeps_clear_of_doors(ifc):
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    checked = 0
    for door in ifc.by_type("IfcDoor"):
        matrix = ifcopenshell.util.placement.get_local_placement(door.ObjectPlacement)
        start = matrix[:3, 3]
        end = start + matrix[:3, 0] * door.OverallWidth
        threshold = LineString([start[0:2], end[0:2]]).buffer(0.4, cap_style=2)
        for flight in ifc.by_type("IfcStairFlight"):
            verts = ifcopenshell.geom.create_shape(settings, flight).geometry.verts
            for x, y, z in zip(verts[0::3], verts[1::3], verts[2::3]):
                # nothing in the way between the floor and the door head
                if start[2] + 0.1 < z < start[2] + 2.0:
                    assert not threshold.contains(
                        LineString([[x, y], [x, y + 0.001]])
                    ), (door.Name, flight.Name)
            checked += 1
    assert checked


@pytest.mark.parametrize(
    "stair, other",
    [
        (
            [[0, 0], [4, 0], [5, 3], [2, 5.5], [-1, 3]],
            [[4, 0], [9, 0], [9, 3], [5, 3]],
        ),
        ([[0, 0], [6, 0], [0, 6]], [[0, 0], [0, 6], [-4, 6], [-4, 0]]),
        ([[0, 0], [5, 0], [4, 3.2], [1, 3.2]], [[5, 0], [9, 0], [9, 3.2], [4, 3.2]]),
    ],
)
def test_stair_in_cells_that_are_not_rectangles(stair, other):
    ifc = build(stair, other, degrees=20.0)
    stairs = ifc.by_type("IfcStair")
    assert len(stairs) == 2
    for stair_element in stairs:
        for part in ifcopenshell.util.element.get_decomposition(stair_element):
            # all the geometry is valid
            assert extents(part)
        pset = ifcopenshell.util.element.get_psets(stair_element)["Pset_StairCommon"]
        assert pset["TreadLength"] >= 0.25


def test_no_stair_without_a_stair_cell_above():
    ifc = build(RECTANGLE, [[3, 0], [8, 0], [8, 5], [3, 5]], storeys=1)
    assert len(ifc.by_type("IfcStair")) == 0


def test_one_entrance_to_a_circulation_cell():
    rooms = [
        {
            "vertices": [[0, 0], [3, 0], [3, 6], [0, 6]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "circulation",
        },
        {
            "vertices": [[3, 0], [8, 0], [8, 6], [3, 6]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "living",
        },
    ]
    faces, widgets = rooms_to_faces_and_widgets(rooms)
    molior_object = Molior.from_faces_and_widgets(
        faces=faces,
        widgets=widgets,
        name="entrance test",
        share_dir=os.path.join(ROOT, "share"),
    )
    molior_object.execute()
    entrances = [
        door
        for door in molior_object.file.by_type("IfcDoor")
        if door.Name == "house entrance"
    ]
    assert len(entrances) == 1
    # in the longest outside wall
    matrix = ifcopenshell.util.placement.get_local_placement(
        entrances[0].ObjectPlacement
    )
    assert abs(matrix[1][0]) == pytest.approx(1.0)
    assert matrix[0][3] < 0.0


def test_circulation_stair_is_a_stair():
    # homemaker-layout calls its stair shafts 'circulation_stair'
    ifc = build(
        RECTANGLE,
        [[3, 0], [8, 0], [8, 5], [3, 5]],
        storeys=2,
        stair_usage="circulation_stair",
    )
    assert len(ifc.by_type("IfcStair")) == 1
    names = [space.Name.split("/")[0] for space in ifc.by_type("IfcSpace")]
    assert names.count("stair-space") == 2
