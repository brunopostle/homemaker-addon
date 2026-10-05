"""Stairs that wind around the perimeter of a stair cell

A stair cell is a cell with 'stair' usage that has another stair cell above
it. The stair occupies a strip against the walls, leaving a well in the
middle, and descends from a landing at the floor above to the floor of this
cell. Corners are turned with winders, or with a quarter landing when there
is room to spare.

Doors decide where everything goes: each floor needs a level landing in front
of its doors, a flight has to avoid the doors of the floor it leaves and the
floor it arrives at. So the stair is planned for the whole stack of cells at
once, from the top down, once for each direction of rotation; the direction
that fits best is used, with a preference for the traditional stair that
rises clockwise.

This works both ways: before any walls are built door_targets() decides where
the doors around a stack of stair cells ought to go so that they leave room
for the stair, and the walls oblige as best they can.

The cell can be any convex polygon, the cells in a stack are expected to
share more-or-less the same plan.
"""

import math

import numpy as np
import ifcopenshell.api.aggregate
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.style
import ifcopenshell.util.element
import ifcopenshell.util.placement
from ifcopenshell.util.shape_builder import ShapeBuilder
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from .baseclass import TraceClass
from .geometry import matrix_align
from .ifc import (
    add_pset,
    add_cell_topology_epsets,
    assign_storey_byindex,
    get_context_by_name,
    get_parent_building,
)

api = ifcopenshell.api

TOLERANCE = 1e-6
ANTICLOCKWISE = 1  # descends anti-clockwise, i.e. rises clockwise
CLOCKWISE = -1  # descends clockwise, i.e. rises anti-clockwise


def risers_number(height, max_riser):
    """Number of risers needed to climb a floor-to-floor height"""
    number = height / max_riser
    if abs(number - round(number)) < TOLERANCE:
        return max(int(round(number)), 1)
    return int(number) + 1


def ideal_going(riser):
    """An 'ideal' going distance: 2 x riser + going = 625mm, not less than
    220mm, rounded-up to the nearest 5mm"""
    going = 0.625 - (2 * riser)
    if going < 0.22:
        return 0.22
    return math.ceil(going * 200 - TOLERANCE) / 200


def mirror(point):
    """Reflect a 2D point, this swaps clockwise for anti-clockwise"""
    return [-point[0], point[1]]


def simplify_polygon(points):
    """Remove duplicate and collinear points from a closed 2D polygon"""
    points = [np.array(point[0:2], dtype=float) for point in points]
    result = []
    for index, point in enumerate(points):
        before = points[index - 1]
        after = points[(index + 1) % len(points)]
        if np.linalg.norm(point - before) < TOLERANCE:
            continue
        a = point - before
        b = after - point
        if np.linalg.norm(b) < TOLERANCE:
            # the next point is a duplicate, look one further on
            b = points[(index + 2) % len(points)] - point
        cross = a[0] * b[1] - a[1] * b[0]
        if abs(cross) < 1e-4 * np.linalg.norm(a) * np.linalg.norm(b):
            continue
        result.append(point)
    return result


class Ring:
    """A strip of constant width inside the perimeter of a convex polygon.

    The polygon is anti-clockwise. A position on the strip is a 'station',
    the distance travelled anti-clockwise along the polygon from the first
    corner. The strip is divided into a 'kite' at each corner and a
    rectangular 'run' along each edge; the inside corners of the strip are
    'newels'."""

    def __init__(self, polygon, width):
        self.corner = simplify_polygon(polygon)
        self.count = len(self.corner)
        if self.count < 3:
            raise ValueError("not a polygon")
        self.direction = []
        self.inward = []
        self.length = []
        for index in range(self.count):
            vector = self.corner[(index + 1) % self.count] - self.corner[index]
            length = np.linalg.norm(vector)
            self.length.append(length)
            self.direction.append(vector / length)
            self.inward.append(np.array([-vector[1], vector[0]]) / length)
        self.turn = []
        for index in range(self.count):
            a = self.direction[index - 1]
            b = self.direction[index]
            turn = math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])
            if turn <= 0.0:
                raise ValueError("not a convex anti-clockwise polygon")
            self.turn.append(turn)
        tangent = [math.tan(turn / 2) for turn in self.turn]

        # the strip can't be wider than this without the well turning inside-out
        self.width = width
        for index in range(self.count):
            limit = self.length[index] / (
                tangent[index] + tangent[(index + 1) % self.count]
            )
            self.width = min(self.width, limit)

        self.start = [0.0]
        for index in range(self.count):
            self.start.append(self.start[-1] + self.length[index])
        self.perimeter = self.start.pop()
        # distance from each corner to the ends of the adjacent runs
        self.setback = [self.width * value for value in tangent]
        self.newel = [
            self.corner[index]
            + self.direction[index] * self.setback[index]
            + self.inward[index] * self.width
            for index in range(self.count)
        ]

        # kites and runs in order, the first kite straddles station zero
        self.pieces = []
        for index in range(self.count):
            after = (index + 1) % self.count
            self.pieces.append(
                {
                    "kind": "kite",
                    "index": index,
                    "lo": self.start[index] - self.setback[index],
                    "hi": self.start[index] + self.setback[index],
                }
            )
            self.pieces.append(
                {
                    "kind": "run",
                    "index": index,
                    "lo": self.start[index] + self.setback[index],
                    "hi": self.start[index] + self.length[index] - self.setback[after],
                }
            )

    def winders(self, index):
        """Number of winders needed to turn a corner, 30 degrees each"""
        return max(1, int(round(math.degrees(self.turn[index]) / 30.0)))

    def station(self, point):
        """Station of the place on the perimeter closest to a 2D point"""
        point = np.array(point[0:2], dtype=float)
        best = None
        for index in range(self.count):
            along = float(np.dot(point - self.corner[index], self.direction[index]))
            along = min(max(along, 0.0), self.length[index])
            nearest = self.corner[index] + self.direction[index] * along
            distance = np.linalg.norm(point - nearest)
            if best is None or distance < best[0]:
                best = (distance, self.start[index] + along)
        return best[1]

    def locate(self, station):
        """The piece at a station, and the station shifted to match it"""
        base = self.pieces[0]["lo"]
        station = base + ((station - base) % self.perimeter)
        for piece in self.pieces:
            if station <= piece["hi"] + TOLERANCE and piece["hi"] - piece["lo"] > 0.0:
                return piece, station
        return self.pieces[0], station - self.perimeter

    def point_outer(self, station):
        """2D point on the perimeter"""
        base = self.start[0]
        station = base + ((station - base) % self.perimeter)
        for index in reversed(range(self.count)):
            if station >= self.start[index]:
                return self.corner[index] + self.direction[index] * (
                    station - self.start[index]
                )
        return self.corner[0]

    def point_inner(self, station):
        """2D point on the inside edge of the strip, a newel if in a kite"""
        piece, station = self.locate(station)
        index = piece["index"]
        if piece["kind"] == "kite":
            return self.newel[index]
        return (
            self.corner[index]
            + self.direction[index] * (station - self.start[index])
            + self.inward[index] * self.width
        )

    def snap(self, station, forward):
        """If a station is within a kite, move it to the end of the kite"""
        piece, shifted = self.locate(station)
        if piece["kind"] == "kite":
            if shifted > piece["lo"] + TOLERANCE and shifted < piece["hi"] - TOLERANCE:
                if forward:
                    return station + piece["hi"] - shifted
                return station + piece["lo"] - shifted
        return station

    def between(self, lo, hi):
        """Pieces, clipped, between two stations. Only entire kites are returned"""
        result = []
        if hi - lo < TOLERANCE:
            return result
        base = self.pieces[0]["lo"]
        loop = math.floor((lo - base) / self.perimeter) - 1
        while base + loop * self.perimeter < hi:
            shift = loop * self.perimeter
            for piece in self.pieces:
                piece_lo = piece["lo"] + shift
                piece_hi = piece["hi"] + shift
                if piece_hi - piece_lo < TOLERANCE:
                    continue
                if piece["kind"] == "kite":
                    if piece_lo < lo - TOLERANCE or piece_hi > hi + TOLERANCE:
                        continue
                else:
                    piece_lo = max(piece_lo, lo)
                    piece_hi = min(piece_hi, hi)
                    if piece_hi - piece_lo < TOLERANCE:
                        continue
                result.append(
                    {
                        "kind": piece["kind"],
                        "index": piece["index"],
                        "lo": piece_lo,
                        "hi": piece_hi,
                    }
                )
            loop += 1
        return result

    def polygon_run(self, index, lo, hi):
        """Part of a run as a 2D polygon"""
        return [
            self.point_outer(lo),
            self.point_outer(hi),
            self.point_outer(hi) + self.inward[index] * self.width,
            self.point_outer(lo) + self.inward[index] * self.width,
        ]

    def polygon_kite(self, index):
        """An entire corner as a 2D polygon"""
        return [
            self.newel[index],
            self.corner[index] - self.direction[index - 1] * self.setback[index],
            self.corner[index],
            self.corner[index] + self.direction[index] * self.setback[index],
        ]

    def polygons_winders(self, index, number):
        """A corner split into wedges radiating from the newel"""
        newel = self.newel[index]
        turn = self.turn[index]
        foot_before = (
            self.corner[index] - self.direction[index - 1] * self.setback[index]
        )
        foot_after = self.corner[index] + self.direction[index] * self.setback[index]

        def boundary(angle):
            if angle <= turn / 2:
                return foot_before + self.direction[index - 1] * self.width * math.tan(
                    angle
                )
            return foot_after - self.direction[index] * self.width * math.tan(
                turn - angle
            )

        polygons = []
        for winder in range(number):
            angle_a = turn * winder / number
            angle_b = turn * (winder + 1) / number
            polygon = [newel, boundary(angle_a)]
            if angle_a < turn / 2 - TOLERANCE and angle_b > turn / 2 + TOLERANCE:
                polygon.append(self.corner[index])
            polygon.append(boundary(angle_b))
            polygons.append(polygon)
        return polygons

    def polygon_well(self):
        """The hole in the middle"""
        return list(self.newel)


def subtract_intervals(spans, intervals, perimeter):
    """Remove [start, length] intervals of a circle from [lo, hi] spans"""
    for start, length in intervals:
        for span in list(spans):
            # the first copy of this interval that ends after the span starts
            first = (
                start + math.ceil((span[0] - start - length) / perimeter) * perimeter
            )
            while first < span[1]:
                remains = []
                for lo, hi in spans:
                    if first + length <= lo or first >= hi:
                        remains.append([lo, hi])
                        continue
                    if first > lo:
                        remains.append([lo, first])
                    if first + length < hi:
                        remains.append([first + length, hi])
                spans = remains
                first += perimeter
    return spans


def capacity(ring, lo, hi, going):
    """Number of treads that fit between two stations, turning corners with winders"""
    total = 0
    for piece in ring.between(lo, hi):
        if piece["kind"] == "kite":
            total += ring.winders(piece["index"])
        else:
            total += int((piece["hi"] - piece["lo"]) / going + TOLERANCE)
    return total


def layout_exact(ring, pieces, treads, going, use_winders):
    """Fit treads of an exact going, working backwards from the bottom.
    Returns a list of pieces, top first, each with a number of 'steps'"""
    remaining = treads
    items = []
    for piece in reversed(pieces):
        if remaining == 0:
            break
        item = dict(piece)
        if piece["kind"] == "kite":
            steps = ring.winders(piece["index"]) if use_winders else 1
            item["steps"] = min(steps, remaining)
        else:
            steps = int((piece["hi"] - piece["lo"]) / going + TOLERANCE)
            if steps == 0 and not items:
                # too short for a tread, leave it as part of the floor below
                continue
            if steps >= remaining:
                item["lo"] = piece["hi"] - remaining * going
                steps = remaining
            item["steps"] = steps
        remaining -= item["steps"]
        items.append(item)
    if remaining > 0:
        return None
    items.reverse()
    return items


def layout_squeezed(ring, pieces, treads):
    """Fit treads into a space that is too small by reducing the going"""
    items = [dict(piece) for piece in pieces]
    kites = [item for item in items if item["kind"] == "kite"]
    runs = [item for item in items if item["kind"] == "run"]
    for item in kites:
        item["steps"] = ring.winders(item["index"])
    for item in runs:
        item["steps"] = 0
    length = sum(item["hi"] - item["lo"] for item in runs)
    spare = treads - sum(item["steps"] for item in kites)
    while spare < 0:
        # more winders than treads
        widest = max(kites, key=lambda item: item["steps"])
        widest["steps"] -= 1
        spare += 1
    if runs and length > TOLERANCE:
        # share between the runs in proportion to length, largest remainder first
        shares = [spare * (item["hi"] - item["lo"]) / length for item in runs]
        for item, share in zip(runs, shares):
            item["steps"] = int(share)
        leftover = spare - sum(item["steps"] for item in runs)
        order = sorted(
            range(len(runs)), key=lambda i: shares[i] - int(shares[i]), reverse=True
        )
        for index in order[:leftover]:
            runs[index]["steps"] += 1
    elif kites:
        for index in range(spare):
            kites[index % len(kites)]["steps"] += 1
    else:
        return None
    return items


def flight_spans(ring, doors_top, doors_bottom, limit, going):
    """Places where a single flight of stairs could go.

    ring: the Ring to fit the flight to, the flight descends anti-clockwise
    doors_top: [station, length] intervals to be kept level at the upper floor
    doors_bottom: [station, length] intervals to be kept level at the lower floor
    limit: station of the foot of the flight above, the upper landing starts here
    going: preferred going

    Returns a list of [capacity in treads, station, station], best first
    """
    perimeter = ring.perimeter

    if limit is not None:
        # the upper landing continues from the flight above, past all the doors
        reach = 0.0
        for start, length in doors_top:
            distance = (start - limit) % perimeter
            if distance + length > perimeter:
                distance -= perimeter
            reach = max(reach, distance + length)
        if reach >= perimeter:
            return []
        spans = [[limit + reach, limit + perimeter]]
    else:
        # we are free to start between any pair of doors
        if doors_top:
            base = doors_top[0][0] + doors_top[0][1]
        elif doors_bottom:
            base = doors_bottom[0][0] + doors_bottom[0][1]
        else:
            base = ring.pieces[0]["lo"]
        spans = subtract_intervals([[base, base + perimeter]], doors_top, perimeter)
    # ..and a flight can't land in front of a door
    spans = subtract_intervals(spans, doors_bottom, perimeter)

    results = []
    for lo, hi in spans:
        lo = ring.snap(lo, True)
        hi = ring.snap(hi, False)
        if hi - lo < TOLERANCE:
            continue
        results.append([capacity(ring, lo, hi, going), lo, hi])
    results.sort(key=lambda result: result[0], reverse=True)
    return results


def plan_flight(ring, span, limit, treads, going):
    """Fit a single flight of stairs between two stations, see flight_spans().

    Returns a dictionary, or None if this isn't possible:
    'landing': [station, station] arc that is level at the upper floor
    'head', 'foot': stations of the top and bottom of the flight
    'items': pieces of the Ring, top first, each with a number of 'steps'
    'fit': capacity as a proportion of the treads needed, less than 1.0 is bad
    """
    number, lo, hi = span
    pieces = ring.between(lo, hi)
    items = layout_exact(ring, pieces, treads, going, False)
    if items is None:
        items = layout_exact(ring, pieces, treads, going, True)
    if items is None:
        items = layout_squeezed(ring, pieces, treads)
    if not items:
        return None
    head = items[0]["lo"]
    foot = items[-1]["hi"]
    if limit is None:
        # everywhere that isn't the flight
        landing = [foot - ring.perimeter, head]
    else:
        landing = [head - ((head - limit) % ring.perimeter), head]
    return {
        "landing": landing,
        "head": head,
        "foot": foot,
        "items": items,
        "fit": number / treads if treads else 1.0,
        "ring": ring,
    }


def plan_stack(levels, rotation=ANTICLOCKWISE, limit_point=None):
    """Plan every flight in a stack of stair cells for one direction of rotation.

    levels: a list of dictionaries, top first, one for each cell with a flight:
    'polygon': 2D anti-clockwise outline of the inside of the cell
    'width': clear width of the stair
    'treads': number of treads
    'going': preferred going
    'doors_top': [[x, y], half_width, is_external] list of doors on the floor above
    'doors_bottom': the same for the floor of this cell

    Where a flight goes changes what is possible for the flights below, so
    this tries the alternatives and keeps whatever is best for the worst flight.

    Returns a list of plans, see plan_flight(), with 'rotation' added, None
    where there is no stair; and the worst 'fit' of them all.
    """
    if not levels:
        return [], None
    level = levels[0]
    polygon = level["polygon"]
    if rotation == CLOCKWISE:
        polygon = [mirror(point) for point in reversed(polygon)]
    try:
        ring = Ring(polygon, level["width"])
    except ValueError:
        return [None] + plan_stack(levels[1:], rotation)[0], 0.0

    intervals = []
    for doors in level["doors_top"], level["doors_bottom"]:
        intervals.append([])
        for point, half_width, *_ in doors:
            if rotation == CLOCKWISE:
                point = mirror(point)
            intervals[-1].append([ring.station(point) - half_width, half_width * 2])
    limit = None
    if limit_point is not None:
        limit = ring.station(limit_point)

    best = None
    spans = flight_spans(ring, intervals[0], intervals[1], limit, level["going"])
    for span in spans[:3]:
        plan = plan_flight(ring, span, limit, level["treads"], level["going"])
        if plan is None:
            continue
        plan["rotation"] = rotation
        plans, worst = plan_stack(levels[1:], rotation, ring.point_outer(plan["foot"]))
        if worst is None or plan["fit"] < worst:
            worst = plan["fit"]
        if best is None or min(worst, 1.0) > min(best[1], 1.0) + TOLERANCE:
            best = ([plan] + plans, worst)
        if worst >= 1.0:
            break
    if best is None:
        return [None] + plan_stack(levels[1:], rotation)[0], 0.0
    return best


def plan_best(levels):
    """Plan a stack of stair cells and return whatever fits best.

    A stair that rises clockwise is preferred. If the stair doesn't fit then
    doors to the outside are ignored, there are often more than are needed
    and they will have to be sacrificed"""
    best = None
    for hard in False, True:
        if hard:
            levels = [dict(level) for level in levels]
            for level in levels:
                for key in "doors_top", "doors_bottom":
                    level[key] = [door for door in level[key] if not door[2]]
        for rotation in ANTICLOCKWISE, CLOCKWISE:
            plans, fit = plan_stack(levels, rotation)
            if fit is None or fit >= 1.0:
                return plans
            if best is None or fit > best[1] + TOLERANCE:
                best = (plans, fit)
    return best[0]


def plan_treads(plan):
    """Expand a plan into individual treads, top first.
    Each is [2D polygon, number of risers below the upper floor, station]"""
    ring = plan["ring"]
    treads = []
    level = 0
    for item in plan["items"]:
        index = item["index"]
        steps = item["steps"]
        if item["kind"] == "kite":
            if steps < 2:
                level += steps
                treads.append([ring.polygon_kite(index), level, item["hi"]])
            else:
                for polygon in ring.polygons_winders(index, steps):
                    level += 1
                    treads.append([polygon, level, item["hi"]])
        elif steps == 0:
            # too short for a tread, extend the tread above
            treads.append(
                [ring.polygon_run(index, item["lo"], item["hi"]), level, item["hi"]]
            )
        else:
            going = (item["hi"] - item["lo"]) / steps
            for step in range(steps):
                level += 1
                lo = item["lo"] + step * going
                treads.append(
                    [ring.polygon_run(index, lo, lo + going), level, lo + going]
                )
    return treads


def plan_landing(plan, is_top):
    """2D polygons that make-up the landing at the upper floor. The landing
    at the top of a stack is the entire cell, apart from a hole for the flight"""
    ring = plan["ring"]
    if is_top:
        lo = plan["foot"] - ring.perimeter
        polygons = [ring.polygon_well()]
    else:
        lo = ring.snap(plan["landing"][0], False)
        polygons = []
    hi = plan["head"]
    if hi - lo > ring.perimeter:
        lo = hi - ring.perimeter
    for piece in ring.between(lo, hi):
        if piece["kind"] == "kite":
            polygons.append(ring.polygon_kite(piece["index"]))
        else:
            polygons.append(ring.polygon_run(piece["index"], piece["lo"], piece["hi"]))
    return polygons, lo, hi


def edge_points(ring, lo, hi):
    """2D points following the inside edge of a Ring between two stations"""
    points = [ring.point_inner(lo)]
    for piece in ring.between(lo, hi):
        if piece["kind"] == "kite":
            points.append(ring.newel[piece["index"]])
    points.append(ring.point_inner(hi))
    return points


def plan_doors(ring, faces, slot=1.2):
    """Decide where the doors around a stack of stair cells ought to go.

    Doors that are bunched together leave more room for the stair. This finds
    the shortest arc of the Ring that has room for a door in each wall that
    needs one, and no more than one of the walls where a door is optional.

    faces: a list of dictionaries, one for each wall that can have a door:
    'key': something to identify the wall
    'lo', 'hi': stations of each end of the wall
    'optional': True if this wall doesn't need a door
    slot: the length of wall that a door needs

    Returns a dictionary with a station for the centre of each door, None for
    optional walls that are to go without.
    """
    perimeter = ring.perimeter
    required = [face for face in faces if not face["optional"]]
    optional = [face for face in faces if face["optional"]]

    def shortest_arc(chosen):
        best = None
        for first in chosen:
            width_first = min(slot, first["hi"] - first["lo"])
            for start in first["lo"], first["hi"] - width_first:
                length = 0.0
                places = {}
                for face in chosen:
                    width = min(slot, face["hi"] - face["lo"])
                    distance = (face["lo"] - start) % perimeter
                    place = start + distance
                    overlap = distance + face["hi"] - face["lo"] - perimeter
                    if overlap >= width - TOLERANCE:
                        # this wall straddles the start and there is room for a door
                        place = start
                    places[face["key"]] = place + width / 2
                    length = max(length, place + width - start)
                if best is None or length < best[0] - TOLERANCE:
                    best = (length, places)
        return best

    result = {face["key"]: None for face in optional}
    best = None
    # a door needs a wall that is long enough, prefer the longest
    candidates = sorted(optional, key=lambda face: face["lo"] - face["hi"])
    usable = [face for face in candidates if face["hi"] - face["lo"] >= slot + 0.6]
    for face in usable or candidates[:1]:
        arc = shortest_arc(required + [face])
        if best is None or arc[0] < best[0] - TOLERANCE:
            best = arc
    if best is None and required:
        best = shortest_arc(required)
    if best is not None:
        result.update(best[1])
    return result


def door_targets(cellcomplex, circulation, elevations):
    """Where doors ought to go in the walls around each stack of stair cells.

    Returns a dictionary keyed by Face index: a 2D point for the centre of
    the door, or None if this wall shouldn't be given an entrance door. Walls
    that aren't mentioned can do as they please.

    The wall code puts an entrance in every outside wall of a ground floor
    stair or circulation cell, one is enough: other circulation cells keep
    the entrance in their longest outside wall.
    """
    targets = {}
    planned = []
    cells_ptr = []
    cellcomplex.Cells(None, cells_ptr)
    for cell in cells_ptr:
        if cell.Usage() != "stair":
            continue
        # start with the cell at the bottom of each stack
        below_ptr = []
        cell.CellsBelow(cellcomplex, below_ptr)
        if any(other.Usage() == "stair" for other in below_ptr):
            continue
        stack = [cell]
        while True:
            above_ptr = []
            stack[-1].CellsAbove(cellcomplex, above_ptr)
            above = [
                other
                for other in above_ptr
                if other.Usage() == "stair"
                and not any(other.IsSame(seen) for seen in stack)
            ]
            if not above:
                break
            stack.append(above[0])
        if len(stack) < 2:
            continue

        ring = None
        faces = []
        for stack_cell in stack:
            graph = stack_cell.Perimeter(cellcomplex).graph
            edges = [graph[node][1] for node in graph]
            if ring is None:
                try:
                    ring = Ring(
                        [edge["start_vertex"].Coordinates()[0:2] for edge in edges],
                        1.0,
                    )
                except ValueError:
                    break
            for edge in edges:
                face = edge["face"]
                key = face.Get("index")
                if key is None:
                    continue
                other = edge["front_cell"]
                if other is None:
                    # the wall code puts an entrance in every ground floor wall
                    if elevations.get(stack_cell.Elevation()) != 0:
                        continue
                    optional = True
                elif other.Usage() == "outside":
                    optional = False
                elif face.GraphVertex(circulation) is not None:
                    optional = False
                else:
                    continue
                start = edge["start_vertex"].Coordinates()[0:2]
                end = edge["end_vertex"].Coordinates()[0:2]
                length = float(np.linalg.norm(np.subtract(end, start)))
                # doors can't go right into the corner
                margin = min(0.25, length / 4)
                lo = ring.station(start)
                faces.append(
                    {
                        "key": key,
                        "lo": lo + margin,
                        "hi": lo + length - margin,
                        "optional": optional,
                    }
                )
        if ring is None or not faces:
            continue
        planned.extend(stack)
        for key, station in plan_doors(ring, faces).items():
            if station is None:
                targets[key] = None
            else:
                targets[key] = [float(value) for value in ring.point_outer(station)]

    for cell in cells_ptr:
        if cell.Usage() not in ("circulation", "stair"):
            continue
        if elevations.get(cell.Elevation()) != 0:
            continue
        if any(cell.IsSame(other) for other in planned):
            continue
        outside = []
        graph = cell.Perimeter(cellcomplex).graph
        for node in graph:
            edge = graph[node][1]
            key = edge["face"].Get("index")
            if edge["front_cell"] is not None or key is None:
                continue
            start = edge["start_vertex"].Coordinates()[0:2]
            end = edge["end_vertex"].Coordinates()[0:2]
            outside.append([float(np.linalg.norm(np.subtract(end, start))), key])
        outside.sort(key=lambda item: item[0], reverse=True)
        for _, key in outside[1:]:
            targets[key] = None
    return targets


class Stair(TraceClass):
    """A stair filling a single storey extruded space"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.ifc = "IfcStair"
        self.path = []
        # widest stair, including 'inner', narrow cells get a narrower stair.
        # width and riser are the defaults of the homemaker-layout scorer
        # (and of Urb before it), which decides if a cell can hold a stair
        self.width = 1.25
        # tallest riser
        self.riser = 0.21
        # 'going' is derived from the riser unless set
        self.going = None
        self.inner = 0.08
        self.thickness = 0.2
        self.handrail = 0.9
        # how far a landing extends either side of the centre of a door
        self.door_margin = 0.15
        # a stair that doesn't fit is squeezed, but not into less than this
        # proportion of the space it needs
        self.worst_fit = 0.6
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc. Run this after any doors have been created"""
        if getattr(self, "cellcomplex", None) is None or not self.closed:
            return
        cell = self.chain.graph[next(iter(self.chain.graph))][1]["back_cell"]
        if type(cell).__name__ != "Cell":
            return
        stack = self.stack(cell)
        if len(stack) < 2 or stack[0].IsSame(cell):
            # nowhere to go
            return

        doors = self.doors()
        floors = []
        for stack_cell in stack:
            polygon = self.cell_polygon(stack_cell)
            elevation = stack_cell.Elevation()
            floors.append(
                {
                    "cell": stack_cell,
                    "polygon": polygon,
                    "height": stack_cell.Height(),
                    "doors": self.doors_polygon(doors, polygon, elevation),
                }
            )
        levels = []
        mine = None
        for index in range(1, len(floors)):
            floor = floors[index]
            risers = risers_number(floor["height"], self.riser)
            going = self.going or ideal_going(floor["height"] / risers)
            if floor["cell"].IsSame(cell):
                mine = index - 1
            levels.append(
                {
                    "polygon": floor["polygon"],
                    "width": self.width - self.inner,
                    "treads": risers - 1,
                    "going": going,
                    "doors_top": floors[index - 1]["doors"],
                    "doors_bottom": floor["doors"],
                }
            )
        if mine is None:
            return
        plan = plan_best(levels)[mine]
        if plan is None or plan["fit"] < self.worst_fit:
            # not even with a going that is far too short
            return
        self.build(cell, plan, levels[mine]["treads"] + 1, mine == 0)

    def stack(self, cell):
        """Stair cells above and below this cell, top first"""
        stack = [cell]
        for method, position in ("CellsAbove", 0), ("CellsBelow", len(stack)):
            current = cell
            while True:
                cells_ptr = []
                getattr(current, method)(self.cellcomplex, cells_ptr)
                found = [
                    other
                    for other in cells_ptr
                    if other.Usage() == "stair"
                    and not any(other.IsSame(seen) for seen in stack)
                ]
                if not found:
                    break
                current = found[0]
                if position == 0:
                    stack.insert(0, current)
                else:
                    stack.append(current)
        return stack

    def cell_polygon(self, cell):
        """2D anti-clockwise outline of the inside face of the walls of a cell"""
        graph = cell.Perimeter(self.cellcomplex).graph
        points = [graph[node][1]["start_vertex"].Coordinates()[0:2] for node in graph]
        if len(points) < 3:
            return []
        polygon = Polygon(points).buffer(-self.inner, join_style=2)
        if polygon.is_empty or not isinstance(polygon, Polygon):
            return []
        return [list(point) for point in orient(polygon).exterior.coords[:-1]]

    def doors(self):
        """All the doors in the building as [centre, direction, half width, is external]"""
        doors = []
        for door in self.file.by_type("IfcDoor"):
            if door.ObjectPlacement is None or not door.OverallWidth:
                continue
            if get_parent_building(door) != self.building:
                continue
            matrix = ifcopenshell.util.placement.get_local_placement(
                door.ObjectPlacement
            )
            direction = matrix[:3, 0]
            centre = matrix[:3, 3] + direction * door.OverallWidth / 2
            topology = ifcopenshell.util.element.get_psets(door).get(
                "EPset_Topology", {}
            )
            is_external = "FrontCellIndex" not in topology
            doors.append([centre, direction, door.OverallWidth / 2, is_external])
        return doors

    def doors_polygon(self, doors, polygon, elevation):
        """Doors in the walls around a polygon as [[x, y], half width, is external]"""
        result = []
        for centre, direction, half_width, is_external in doors:
            if abs(centre[2] - elevation) > 0.5:
                continue
            for index in range(len(polygon)):
                start = np.array(polygon[index - 1])
                vector = np.array(polygon[index]) - start
                length = np.linalg.norm(vector)
                if length < TOLERANCE:
                    continue
                vector = vector / length
                if abs(float(np.dot(vector, direction[0:2]))) < 0.9:
                    continue
                along = float(np.dot(centre[0:2] - start, vector))
                if along < 0.0 or along > length:
                    continue
                nearest = start + vector * along
                if np.linalg.norm(centre[0:2] - nearest) > 0.6:
                    continue
                result.append(
                    [list(nearest), half_width + self.door_margin, is_external]
                )
                break
        return result

    def build(self, cell, plan, risers, is_top):
        """Draw a planned flight, the landing above it, and a handrail"""
        ring = plan["ring"]
        riser = self.height / risers
        builder = ShapeBuilder(self.file)
        body_context = get_context_by_name(self.file, context_identifier="Body")
        style = self.surface_style()
        matrix = matrix_align([0.0, 0.0, self.elevation], [1.0, 0.0, 0.0])

        def outside(points):
            # back to the real world
            if plan["rotation"] == CLOCKWISE:
                return [mirror(point) for point in points]
            return [[float(point[0]), float(point[1])] for point in points]

        def extrude(polygon, bottom, top):
            exterior = builder.polyline(
                outside(polygon.exterior.coords[:-1]), closed=True
            )
            interiors = [
                builder.polyline(outside(interior.coords[:-1]), closed=True)
                for interior in polygon.interiors
            ]
            return builder.extrude(
                builder.profile(exterior, inner_curves=interiors),
                magnitude=top - bottom,
                position=(0.0, 0.0, bottom),
            )

        def create(ifc_class, name, items, predefined_type=None):
            element = api.root.create_entity(
                self.file,
                ifc_class=ifc_class,
                name=name,
                predefined_type=predefined_type,
            )
            representation = builder.get_representation(body_context, items)
            api.style.assign_representation_styles(
                self.file, shape_representation=representation, styles=[style]
            )
            api.geometry.assign_representation(
                self.file, product=element, representation=representation
            )
            api.geometry.edit_object_placement(
                self.file, product=element, matrix=matrix
            )
            return element

        stair = api.root.create_entity(
            self.file,
            ifc_class=self.ifc,
            name=self.name + "/" + str(cell.Get("index")),
        )
        api.geometry.edit_object_placement(self.file, product=stair, matrix=matrix)
        assign_storey_byindex(self.file, stair, self.building, self.level)
        add_cell_topology_epsets(self.file, stair, cell)
        self.add_psets(stair)
        parts = []

        # flight, each tread overlaps the tread below
        treads = plan_treads(plan)
        solids = []
        for polygon, level, _ in treads:
            top = self.height - level * riser
            bottom = max(top - riser * 2, 0.0)
            if top - bottom < TOLERANCE:
                continue
            solids.append(extrude(orient(Polygon(polygon)), bottom, top))
        flight = create("IfcStairFlight", self.name + "-flight", solids)
        parts.append(flight)
        goings = [
            (item["hi"] - item["lo"]) / item["steps"]
            for item in plan["items"]
            if item["kind"] == "run" and item["steps"] > 0
        ]
        properties = {
            "NumberOfRiser": risers,
            "NumberOfTreads": risers - 1,
            "RiserHeight": riser,
        }
        if goings:
            properties["TreadLength"] = min(goings)
        add_pset(self.file, flight, "Pset_StairFlightCommon", properties)
        add_pset(self.file, stair, "Pset_StairCommon", properties)

        # landing
        polygons, landing_lo, landing_hi = plan_landing(plan, is_top)
        # the pieces share edges, a small overlap makes sure they merge
        landing = (
            unary_union(
                [Polygon(polygon).buffer(0.001, join_style=2) for polygon in polygons]
            )
            .buffer(-0.001, join_style=2)
            .simplify(0.0005)
        )
        if isinstance(landing, Polygon):
            landing = MultiPolygon([landing])
        solids = [
            extrude(orient(polygon), self.height - self.thickness, self.height)
            for polygon in getattr(landing, "geoms", [])
            if polygon.area > TOLERANCE
        ]
        if solids:
            parts.append(create("IfcSlab", self.name + "-landing", solids, "LANDING"))

        # handrail and posts on the inside edge, set-in a little from the edge
        radius = 0.025
        try:
            edge = Ring(ring.corner, ring.width - radius * 2)
        except ValueError:
            edge = ring
        paths = []
        path = []
        if is_top:
            # the hole in the top floor needs guarding
            guard = [[*edge.point_outer(plan["foot"]), self.height]]
            for point in reversed(edge_points(edge, plan["head"], plan["foot"])):
                guard.append([*point, self.height])
            paths.append(guard)
        elif landing_hi - landing_lo > TOLERANCE:
            for point in edge_points(edge, landing_lo, landing_hi):
                path.append([*point, self.height])
        if not path:
            path.append([*edge.point_inner(plan["head"]), self.height])
        for _, level, station in treads:
            path.append([*edge.point_inner(station), self.height - level * riser])
        paths.append(path)

        solids = []
        for path in paths:
            points = []
            for point in path:
                point = [*outside([point])[0], float(point[2])]
                if points and np.linalg.norm(np.subtract(point, points[-1])) < 0.001:
                    continue
                # a post, unless there is already one here
                if (
                    not points
                    or np.linalg.norm(np.subtract(point[0:2], points[-1][0:2])) > 0.001
                ):
                    solids.append(
                        builder.extrude(
                            builder.circle(center=point[0:2], radius=radius / 2),
                            magnitude=self.handrail,
                            position=(0.0, 0.0, point[2]),
                        )
                    )
                points.append(point)
            for index in range(len(points) - 1):
                start = np.array(points[index])
                vector = np.array(points[index + 1]) - start
                length = float(np.linalg.norm(vector))
                vector = vector / length
                # any direction perpendicular to the rail will do
                x_axis = np.cross(vector, [0.0, 0.0, 1.0])
                if np.linalg.norm(x_axis) < TOLERANCE:
                    x_axis = np.array([1.0, 0.0, 0.0])
                x_axis = x_axis / np.linalg.norm(x_axis)
                solids.append(
                    builder.extrude(
                        builder.circle(radius=radius),
                        magnitude=length,
                        position=tuple(start + [0.0, 0.0, self.handrail]),
                        position_z_axis=tuple(vector),
                        position_x_axis=tuple(x_axis),
                    )
                )
        if solids:
            parts.append(
                create("IfcRailing", self.name + "-handrail", solids, "HANDRAIL")
            )

        api.aggregate.assign_object(self.file, products=parts, relating_object=stair)
        return stair

    def surface_style(self):
        """A colour for stairs"""
        for style in self.file.by_type("IfcSurfaceStyle"):
            if style.Name == "Stair":
                return style
        style = api.style.add_style(self.file, name="Stair")
        api.style.add_surface_style(
            self.file,
            style=style,
            ifc_class="IfcSurfaceStyleShading",
            attributes={
                "SurfaceColour": {
                    "Name": None,
                    "Red": 0.7,
                    "Green": 0.6,
                    "Blue": 0.45,
                },
                "Transparency": 0.0,
            },
        )
        return style
