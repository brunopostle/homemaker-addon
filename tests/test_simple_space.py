#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex, Face, Cell

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Molior
import molior.ifc


"""Example showing how to generate Space and Floor objects from Topologic Cells.
"""


@pytest.fixture
def ifc_project():
    """Fixture to set up an IFC project and build a space."""
    # initialise an IFC project
    ifc = molior.ifc.init(name="My Project")

    # the Molior module builds stuff in an IFC file
    molior_builder = Molior(
        file=ifc,
        name="My House",
        elevations={3.15: "Upper Level"},
    )

    # create a Site and Building, and attach to the Project in the IFC
    molior_builder.init_building()

    # Create vertices
    vert = [
        Vertex.ByCoordinates(5.0, 0.0, 3.15),
        Vertex.ByCoordinates(8.0, 4.0, 3.15),
        Vertex.ByCoordinates(4.0, 7.0, 3.15),
        Vertex.ByCoordinates(1.0, 3.0, 3.15),
        Vertex.ByCoordinates(5.0, 0.0, 6.15),
        Vertex.ByCoordinates(8.0, 4.0, 6.15),
        Vertex.ByCoordinates(4.0, 7.0, 6.15),
        Vertex.ByCoordinates(1.0, 3.0, 9.0),
    ]

    # Create faces
    faces = [
        Face.ByVertices([vert[0], vert[1], vert[2], vert[3]]),
        Face.ByVertices([vert[0], vert[1], vert[5], vert[4]]),
        Face.ByVertices([vert[1], vert[2], vert[6], vert[5]]),
        Face.ByVertices([vert[2], vert[3], vert[7], vert[6]]),
        Face.ByVertices([vert[3], vert[0], vert[4], vert[7]]),
        Face.ByVertices([vert[4], vert[5], vert[6]]),
        Face.ByVertices([vert[6], vert[7], vert[4]]),
    ]
    cell = Cell.ByFaces(faces, 0.0001)

    # host_topology would normally be a CellComplex, but we can use our Cell
    host_topology = cell
    perimeter = cell.Perimeter(host_topology)

    molior_builder.build_trace(
        stylename="default",
        condition="living",
        elevation=cell.Elevation(),
        height=cell.Height(),
        chain=perimeter,
    )

    return ifc


def test_write(ifc_project):
    """Test writing the IFC file."""
    ifc_project.write("_test.ifc")
