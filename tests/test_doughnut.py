"""A doughnut shaped room has a hole in its perimeter, around a courtyard"""

import os
import sys

import ifcopenshell.util.element
import pytest
from topologic_core import CellComplex, Face, Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
from topologist.helpers import string_to_coor

OUTER = [[0.0, 0.0], [9.0, 0.0], [9.0, 9.0], [0.0, 9.0]]
INNER = [[3.0, 3.0], [6.0, 3.0], [6.0, 6.0], [3.0, 6.0]]


def polygon(vertices):
    return Face.ByVertices([Vertex.ByCoordinates(*vertex) for vertex in vertices])


def rectangle(x0, y0, x1, y1, z):
    return polygon([[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]])


def walls(corners):
    result = []
    for index in range(4):
        a = corners[index]
        b = corners[(index + 1) % 4]
        result.append(polygon([[*a, 0.0], [*b, 0.0], [*b, 3.0], [*a, 3.0]]))
    return result


def doughnut(courtyard=False):
    """A 9m square room around a 3m square hole, the hole can be a Cell too"""
    faces = walls(OUTER) + walls(INNER)
    for z in (0.0, 3.0):
        faces += [
            rectangle(0.0, 0.0, 9.0, 3.0, z),
            rectangle(0.0, 6.0, 9.0, 9.0, z),
            rectangle(0.0, 3.0, 3.0, 6.0, z),
            rectangle(6.0, 3.0, 9.0, 6.0, z),
        ]
        if courtyard:
            faces.append(rectangle(3.0, 3.0, 6.0, 6.0, z))
    for face in faces:
        face.Set("stylename", "default")
    return faces


def signed_area(perimeter):
    coors = [string_to_coor(node) for node in perimeter.graph]
    return (
        sum(
            coors[index - 1][0] * coors[index][1]
            - coors[index][0] * coors[index - 1][1]
            for index in range(len(coors))
        )
        / 2.0
    )


def the_doughnut(cellcomplex):
    cells_ptr = []
    cellcomplex.Cells(None, cells_ptr)
    return max(cells_ptr, key=lambda cell: cell.PlanArea())


@pytest.mark.parametrize("courtyard", [False, True])
def test_perimeters(courtyard):
    cellcomplex = CellComplex.ByFaces(doughnut(courtyard), 0.0001)
    cellcomplex.AllocateCells([])
    cell = the_doughnut(cellcomplex)
    assert cell.Usage() == "living"

    perimeters = cell.Perimeters(cellcomplex)
    assert len(perimeters) == 2
    outer, hole = perimeters
    assert outer.is_simple_cycle()
    assert hole.is_simple_cycle()
    # anti-clockwise outside, clockwise around the hole
    assert signed_area(outer) == pytest.approx(81.0)
    assert signed_area(hole) == pytest.approx(-9.0)
    for perimeter in perimeters:
        for node in perimeter.graph:
            assert perimeter.graph[node][1]["back_cell"].IsSame(cell)
    # the Perimeter is the outside
    assert sorted(cell.Perimeter(cellcomplex).graph) == sorted(outer.graph)
    # the footprint goes round the hole, unless it is filled by a courtyard
    assert len(cellcomplex.FootPrint()) == (1 if courtyard else 2)


def test_space_has_a_hole():
    molior_object = Molior.from_faces_and_widgets(faces=doughnut(), widgets=[])
    molior_object.execute()
    spaces = molior_object.file.by_type("IfcSpace")
    assert len(spaces) == 1
    solid = spaces[0].Representation.Representations[0].Items[0]
    profile = solid.SweptArea
    assert profile.is_a("IfcArbitraryProfileDefWithVoids")
    assert len(profile.InnerCurves) == 1
    # the hole is offset into the room, the same as the outside
    xs = [point.Coordinates[0] for point in profile.InnerCurves[0].Points]
    assert min(xs) == pytest.approx(3.0 - 0.08)
    assert max(xs) == pytest.approx(6.0 + 0.08)
    xs = [point.Coordinates[0] for point in profile.OuterCurve.Points]
    assert min(xs) == pytest.approx(0.08)
    assert max(xs) == pytest.approx(9.0 - 0.08)
    # walls all round, inside and out
    assert len(molior_object.file.by_type("IfcWall")) >= 8
    assert ifcopenshell.util.element.get_psets(spaces[0])["Qto_SpaceBaseQuantities"][
        "NetFloorArea"
    ] == pytest.approx(72.0)
