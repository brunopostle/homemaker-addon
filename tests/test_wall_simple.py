#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
from molior import Molior
import molior.ifc


class Tests(unittest.TestCase):
    def setUp(self):
        # initialise an IFC project
        self.ifc = molior.ifc.init("My Project")

        # could also supply 'cellcomplex' or 'circulation' graph here
        molior_object = Molior(
            file=self.ifc,
        )

        # parameters are Name and a dictionary of elevations
        molior_object.add_building("My House", {3.15: "Upper Level"})

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

        # retrieve the two bottom vertices
        axis = face.AxisOuter()

        # retrieve the cells for this face
        # back_cell_front_cell = face.CellsOrdered(cellcomplex)

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
        # retrieve the first (and only) path
        path = trace.find_paths()[0]

        molior_object.get_trace_ifc(
            stylename="default",
            condition="external",
            elevation=face.Elevation(),
            height=face.Height(),
            chain=path,
        )

    def test_write(self):
        self.ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
