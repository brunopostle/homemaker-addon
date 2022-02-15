#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ifcopenshell
import molior.ifc
from molior.ifc import create_extruded_area_solid, get_context_by_name

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        self.file = molior.ifc.init(name="Our Project")
        self.body_context = get_context_by_name(self.file, context_identifier="Body")

    def test_add_surface_style(self):
        style = run("style.add_style", self.file, name="Outdoor wall")
        run(
            "style.add_surface_style",
            self.file,
            style=style,
            attributes={
                "SurfaceColour": {
                    "Name": "Orange",
                    "Red": 1.0,
                    "Green": 0.5,
                    "Blue": 0.0,
                },
                "DiffuseColour": {
                    "Name": "White",
                    "Red": 1.0,
                    "Green": 1.0,
                    "Blue": 1.0,
                },
                "Transparency": 0.9,
                "ReflectanceMethod": "MATT",
            },
        )

        shape = self.file.createIfcShapeRepresentation(
            self.body_context,
            self.body_context.ContextIdentifier,
            "SweptSolid",
            [
                create_extruded_area_solid(
                    self.file, [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0]], 3.0
                )
            ],
        )

        run(
            "style.assign_representation_styles",
            self.file,
            shape_representation=shape,
            styles=[style],
        )

        slab = run("root.create_entity", self.file, ifc_class="IfcSlab", name="My Slab")
        run(
            "geometry.assign_representation",
            self.file,
            product=slab,
            representation=shape,
        )

        self.assertEqual(slab.Representation.is_a(), "IfcProductDefinitionShape")
        self.assertEqual(len(slab.Representation.Representations), 1)
        representation = slab.Representation.Representations[0]
        self.assertEqual(len(representation.Items), 1)
        myshape = representation.Items[0]
        for value in self.file.get_inverse(myshape):
            if value.is_a("IfcStyledItem"):
                styled_item = value
        style = styled_item.Styles[0]
        self.assertEqual(style.is_a(), "IfcSurfaceStyle")
        rendering = style.Styles[0]
        self.assertEqual(rendering.is_a(), "IfcSurfaceStyleRendering")
        self.assertEqual(rendering.SurfaceColour.Name, "Orange")

        self.file.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
