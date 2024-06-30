#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api.root
import ifcopenshell.util.element

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_context_by_name,
    add_pset,
    get_type_object,
)
from molior.style import Style

api = ifcopenshell.api


class Tests(unittest.TestCase):
    def setUp(self):
        self.file = molior.ifc.init(name="My Project")
        self.body_context = get_context_by_name(self.file, context_identifier="Body")

        column_type = get_type_object(
            self.file,
            Style(),
            ifc_type="IfcMemberType",
            stylename="framing",
            name="purlin",
        )

        mycolumn = api.root.create_entity(self.file, ifc_class="IfcColumn", name="My Column"
        )
        api.type.assign_type(
            self.file,
            related_objects=[mycolumn],
            relating_type=column_type,
        )

        for material in self.file.by_type("IfcMaterial"):
            add_pset(self.file, material, "some pset name", {"foo": "bar"})

        # test copying materials
        self.another_file = molior.ifc.init(name="My Other Project")
        for entity in self.file.by_type("IfcMaterial"):
            api.project.append_asset(
                self.another_file,
                library=self.file,
                element=entity,
            )

        # an extruded solid
        shape = self.file.createIfcShapeRepresentation(
            self.body_context,
            self.body_context.ContextIdentifier,
            "SweptSolid",
            [
                self.file.createIfcExtrudedAreaSolid(
                    material_profile.Profile,
                    self.file.createIfcAxis2Placement3D(
                        self.file.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                        self.file.createIfcDirection([0.0, 1.0, 0.0]),
                        self.file.createIfcDirection([1.0, 0.0, 0.0]),
                    ),
                    self.file.createIfcDirection([0.0, 0.0, 1.0]),
                    3.0,
                )
                for material_profile in column_type.HasAssociations[
                    0
                ].RelatingMaterial.MaterialProfiles
            ],
        )
        api.geometry.assign_representation(
            self.file,
            product=mycolumn,
            representation=shape,
        )

    def test_write(self):
        self.file.write("_test.ifc")

    def test_copy_material(self):
        self.assertEqual(
            len(self.file.by_type("IfcGeometricRepresentationContext")), 13
        )
        self.assertEqual(
            len(self.another_file.by_type("IfcGeometricRepresentationContext")), 13
        )
        for material in self.another_file.by_type("IfcMaterial"):
            if material.Name == "Cheese":
                self.assertEqual(len(material.HasRepresentation), 0)
                continue

            self.assertEqual(len(material.HasRepresentation), 1)
            self.assertEqual(len(material.HasRepresentation[0].Representations), 1)
            self.assertEqual(
                len(material.HasRepresentation[0].Representations[0].Items), 1
            )
            self.assertEqual(
                len(material.HasRepresentation[0].Representations[0].Items[0].Styles), 1
            )
            self.assertEqual(
                len(
                    material.HasRepresentation[0]
                    .Representations[0]
                    .Items[0]
                    .Styles[0]
                    .Styles
                ),
                1,
            )
            self.assertEqual(
                material.HasRepresentation[0]
                .Representations[0]
                .Items[0]
                .Styles[0]
                .Styles[0]
                .SurfaceColour.is_a(),
                "IfcColourRgb",
            )


if __name__ == "__main__":
    unittest.main()
