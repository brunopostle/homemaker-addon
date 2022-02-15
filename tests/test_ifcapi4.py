#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_extruded_type_by_name,
    get_context_by_name,
)

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        self.file = molior.ifc.init(name="My Project")
        self.body_context = get_context_by_name(self.file, context_identifier="Body")

        column_type = get_extruded_type_by_name(
            self.file,
            style_materials={
                "Cheese": {
                    "surface_colour": [1.0, 0.8, 0.3],
                    "diffuse_colour": [1.0, 0.8, 0.3],
                },
                "Tomato": {
                    "surface_colour": [1.0, 3.0, 0.0],
                    "diffuse_colour": [1.0, 3.0, 0.0],
                },
            },
            profiles=[
                {
                    "ifc_class": "IfcRectangleProfileDef",
                    "material": "Cheese",
                    "parameters": {"ProfileType": "AREA", "XDim": 0.1, "YDim": 0.1},
                    "position": {"Location": [0.2, 0.0], "RefDirection": [1.0, 0.0]},
                },
                {
                    "ifc_class": "IfcIShapeProfileDef",
                    "material": "Tomato",
                    "parameters": {
                        "ProfileType": "AREA",
                        "OverallWidth": 0.1,
                        "OverallDepth": 0.2,
                        "WebThickness": 0.005,
                        "FlangeThickness": 0.01,
                        "FilletRadius": 0.005,
                    },
                    "position": {"Location": [0.0, 0.0], "RefDirection": [1.0, 0.0]},
                },
            ],
        )

        mycolumn = run(
            "root.create_entity", self.file, ifc_class="IfcColumn", name="My Column"
        )
        run(
            "type.assign_type",
            self.file,
            related_object=mycolumn,
            relating_type=column_type,
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
        run(
            "geometry.assign_representation",
            self.file,
            product=mycolumn,
            representation=shape,
        )

    def test_write(self):
        self.file.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
