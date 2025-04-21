#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ushell as ushell
from molior import Molior
import molior.ifc


"""Example showing how to generate arbitrary Slab objects such as Roof surfaces
from Topologic Faces.
"""


@pytest.fixture
def ifc_project():
    """Fixture to set up an IFC project and build a roof."""
    # initialise an IFC project
    ifc = molior.ifc.init(name="My Project")

    # the Molior module builds stuff in an IFC file
    molior_builder = Molior(
        file=ifc,
        name="My House",
        elevations={6.15: "Upper Level"},
    )

    # create a Site and Building, and attach to the Project in the IFC
    molior_builder.init_building()

    # Create roof faces
    face = Face.ByVertices(
        [
            Vertex.ByCoordinates(5.0, 0.0, 6.15),
            Vertex.ByCoordinates(8.0, 4.0, 6.15),
            Vertex.ByCoordinates(1.0, 3.0, 9.0),
        ]
    )
    face2 = Face.ByVertices(
        [
            Vertex.ByCoordinates(8.0, 4.0, 6.15),
            Vertex.ByCoordinates(4.0, 7.0, 6.15),
            Vertex.ByCoordinates(1.0, 3.0, 9.0),
        ]
    )

    # Verify face orientations
    assert not face.IsVertical()
    assert not face.IsHorizontal()
    assert face.IsUpward()
    assert not face2.IsVertical()
    assert not face2.IsHorizontal()
    assert face2.IsUpward()

    # Create a simple shell
    hull = ushell.shell()

    # Add facets to the hull
    vertices = []
    face.VerticesPerimeter(vertices)
    hull.add_facet(
        [vertex.Coordinates() for vertex in vertices],
        {"face": face, "back_cell": None, "front_cell": None},
    )

    vertices2 = []
    face2.VerticesPerimeter(vertices2)
    hull.add_facet(
        [vertex.Coordinates() for vertex in vertices2],
        {"face": face2, "back_cell": None, "front_cell": None},
    )

    # Build the hull
    molior_builder.build_hull(
        stylename="default",
        condition="roof",
        hull=hull,
    )

    return ifc


def test_write(ifc_project):
    """Test writing the IFC file."""
    ifc_project.write("_test.ifc")
