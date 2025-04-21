#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
from molior import Molior
import molior.ifc


"""Example showing how to generate Wall objects from Topologic Faces.
"""


@pytest.fixture
def ifc_project():
    """Fixture to set up an IFC project and build walls."""
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

    # Add a Wall

    # a vertical face with a horizontal bottom edge
    face = Face.ByVertices(
        [
            Vertex.ByCoordinates(5.0, 0.0, 3.15),
            Vertex.ByCoordinates(8.0, 4.0, 3.15),
            Vertex.ByCoordinates(8.0, 4.0, 6.15),
            Vertex.ByCoordinates(5.0, 0.0, 6.15),
        ]
    )
    # another vertical face with a horizontal bottom edge
    face2 = Face.ByVertices(
        [
            Vertex.ByCoordinates(8.0, 4.0, 3.15),
            Vertex.ByCoordinates(4.0, 7.0, 3.15),
            Vertex.ByCoordinates(4.0, 7.0, 6.15),
            Vertex.ByCoordinates(8.0, 4.0, 6.15),
        ]
    )
    # Verify wall faces are vertical
    assert face.IsVertical()
    assert face2.IsVertical()

    # helper method to retrieve the two bottom horizontal vertices
    axis = face.AxisOuter()
    axis2 = face2.AxisOuter()

    # a simple non-branching graph
    trace = ugraph.graph()

    trace.add_edge(
        {
            axis[0].CoorAsString(): [
                axis[1].CoorAsString(),
                {
                    "start_vertex": axis[0],
                    "end_vertex": axis[1],
                    "face": face,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            axis2[0].CoorAsString(): [
                axis2[1].CoorAsString(),
                {
                    "start_vertex": axis2[0],
                    "end_vertex": axis2[1],
                    "face": face2,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )

    # retrieve the first chain or loop from the graph
    path = trace.find_paths()[0]

    molior_builder.build_trace(
        stylename="default",
        condition="external",
        elevation=face.Elevation(),
        height=face.Height(),
        chain=path,
    )

    return ifc


def test_write(ifc_project):
    """Test writing the IFC file."""
    ifc_project.write("_test.ifc")
