#!/usr/bin/python3

import time
from topologic_core import Vertex, Face, Cell, FaceUtility, CellUtility
from topologic_core import CellContainmentState


def test_sliver_face():
    """A roof Face 1.3 mm wide, as CellComplex.ByFaces() made from a hipped
    roof over harbor-house: FaceUtility.InternalVertex(face, 0.001) took hours
    and gigabytes on it, because the centre of mass fails IsInside() at that
    tolerance and every one of ~5.6 million samples fails after it"""
    face = Face.ByVertices(
        [
            Vertex.ByCoordinates(-22.9145, 19.9496, 12.2561),
            Vertex.ByCoordinates(-22.9158, 19.9509, 12.2570),
            Vertex.ByCoordinates(-22.9158, 21.7288, 12.2570),
            Vertex.ByCoordinates(-22.9145, 21.7288, 12.2561),
        ]
    )
    # the condition that sent FaceUtility.InternalVertex() into its search
    assert not FaceUtility.IsInside(face, face.CenterOfMass(), 0.001)

    start = time.process_time()
    vertex = face.InternalVertex()
    assert time.process_time() - start < 1.0
    assert FaceUtility.IsInside(face, vertex, 0.0001)


def test_concave_cell():
    """An L-shaped Cell whose centre of mass is outside it"""
    plan = [(0, 0), (10, 0), (10, 1), (1, 1), (1, 10), (0, 10)]
    bottom = [Vertex.ByCoordinates(x, y, 0.0) for x, y in plan]
    top = [Vertex.ByCoordinates(x, y, 3.0) for x, y in plan]
    faces = [Face.ByVertices(bottom), Face.ByVertices(top)]
    for i in range(len(plan)):
        j = (i + 1) % len(plan)
        faces.append(Face.ByVertices([bottom[i], bottom[j], top[j], top[i]]))
    cell = Cell.ByFaces(faces, 0.0001)

    assert (
        CellUtility.Contains(cell, cell.CenterOfMass(), 0.001)
        == CellContainmentState.OUTSIDE
    )
    vertex = cell.InternalVertex()
    assert CellUtility.Contains(cell, vertex, 0.001) == CellContainmentState.INSIDE
