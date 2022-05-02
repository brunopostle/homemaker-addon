#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
from molior import Molior
import molior.ifc


"""Example showing how to generate Wall objects from Topologic Faces.
"""


class Tests(unittest.TestCase):
    def setUp(self):
        # initialise an IFC project
        self.ifc = molior.ifc.init(name="My Project")

        # the Molior module builds stuff in an IFC file
        molior_builder = Molior(
            file=self.ifc,
            name="My House",
            elevations={3.15: "Upper Level"},
            # cellcomplex=my_cellcomplex,
            # circulation=my_circulation,
        )

        # create a Site and Building, and attach to the Project in the IFC
        # parameters are Name and a dictionary of elevations
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
        # walls require vertical faces
        self.assertTrue(face.IsVertical())
        self.assertTrue(face2.IsVertical())

        # helper method to retrieve the two bottom horizontal vertices
        axis = face.AxisOuter()
        axis2 = face2.AxisOuter()

        # a simple non-branching graph
        trace = ugraph.graph()

        # retrieve the cells for this face if you have a CellComplex
        # back_cell, front_cell = *face.CellsOrdered(cellcomplex)

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

        # fixup structural and spatial model if you have a CellComplex
        # self.connect_structure()
        # self.connect_spaces()

    def test_write(self):
        self.ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
