#!/usr/bin/python3

import os
import sys
import unittest
from topologic import Vertex, Face

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ushell as ushell
from molior import Molior
import molior.ifc


"""Example showing how to generate arbitrary Slab objects such as Roof surfaces
from Topologic Faces.
"""


class Tests(unittest.TestCase):
    def setUp(self):
        # initialise an IFC project
        self.ifc = molior.ifc.init(name="My Project")

        # the Molior module builds stuff in an IFC file
        molior_builder = Molior(
            file=self.ifc,
            name="My House",
            elevations={6.15: "Upper Level"}
            # cellcomplex=my_cellcomplex,
        )

        # create a Site and Building, and attach to the Project in the IFC
        # parameters are Name and a dictionary of elevations
        molior_builder.init_building()

        # Add a Roof

        # an inclined face
        face = Face.ByVertices(
            [
                Vertex.ByCoordinates(5.0, 0.0, 6.15),
                Vertex.ByCoordinates(8.0, 4.0, 6.15),
                Vertex.ByCoordinates(1.0, 3.0, 9.0),
            ]
        )
        # another inclined face
        face2 = Face.ByVertices(
            [
                Vertex.ByCoordinates(8.0, 4.0, 6.15),
                Vertex.ByCoordinates(4.0, 7.0, 6.15),
                Vertex.ByCoordinates(1.0, 3.0, 9.0),
            ]
        )
        # a hull face can have any orientation, but these are tilted up
        self.assertFalse(face.IsVertical())
        self.assertFalse(face.IsHorizontal())
        self.assertTrue(face.IsUpward())
        self.assertFalse(face2.IsVertical())
        self.assertFalse(face2.IsHorizontal())
        self.assertTrue(face2.IsUpward())

        # a simple shell
        hull = ushell.shell()

        # retrieve the cells for this face if you have a CellComplex
        # back_cell, front_cell = *face.CellsOrdered(cellcomplex)

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

        molior_builder.build_hull(
            stylename="default",
            condition="roof",
            hull=hull,
        )

        # fixup structural and spatial model if you have a CellComplex
        # self.connect_structure()
        # self.connect_spaces()

    def test_write(self):
        self.ifc.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
