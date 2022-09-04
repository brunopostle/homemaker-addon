#!/usr/bin/python3

import os
import sys
import unittest
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior.ifc
from molior.ifc import (
    get_context_by_name,
    get_site_by_name,
    get_building_by_name,
    get_library_by_name,
    get_material_by_name,
    get_structural_analysis_model_by_name,
    create_storeys,
)
from molior.style import Style

run = ifcopenshell.api.run


class Tests(unittest.TestCase):
    def setUp(self):
        self.file = molior.ifc.init(name="My Project")
        self.body_context = get_context_by_name(self.file, context_identifier="Body")

        project = self.file.by_type("IfcProject")[0]

        site = get_site_by_name(self.file, project, "My Site")
        building = get_building_by_name(self.file, site, "My Building")
        self.assertEqual(len(self.file.by_type("IfcBuilding")), 1)

        get_site_by_name(self.file, project, "My Site")
        get_building_by_name(self.file, site, "My Building")
        self.assertEqual(len(self.file.by_type("IfcSite")), 1)
        self.assertEqual(len(self.file.by_type("IfcBuilding")), 1)

        get_building_by_name(self.file, site, "My Other Building")
        self.assertEqual(len(self.file.by_type("IfcSite")), 1)
        self.assertEqual(len(self.file.by_type("IfcBuilding")), 2)

        site2 = get_site_by_name(self.file, project, "My Other Site")
        self.assertEqual(len(self.file.by_type("IfcSite")), 2)
        get_building_by_name(self.file, site2, "My Building")
        self.assertEqual(len(self.file.by_type("IfcBuilding")), 3)

        model1 = get_structural_analysis_model_by_name(self.file, building, "My Model")
        get_structural_analysis_model_by_name(self.file, building, "My Model")
        model2 = get_structural_analysis_model_by_name(self.file, building, "My Model")
        self.assertEqual(len(self.file.by_type("IfcStructuralAnalysisModel")), 1)
        self.assertEqual(model1, model2)

        create_storeys(self.file, building, {0.0: 0})

    def test_import_material(self):
        # retrieve a material from an IFC library
        mystyle = Style()
        (stylename, library_file, element) = mystyle.get_from_library(
            "courtyard", "IfcMaterial", "Screed"
        )
        # add to current project
        local_element = run(
            "project.append_asset", self.file, library=library_file, element=element
        )

        # create a library in this project
        library = get_library_by_name(self.file, stylename)
        # this doesn't work because an IFC Material isn't an Object Definition
        # so it doesn't HasContext and can't fit in a Project Library :(
        run(
            "project.assign_declaration",
            self.file,
            definition=local_element,
            relating_context=library,
        )

        # all in one method
        get_material_by_name(self.file, mystyle, stylename="courtyard", name="Concrete")

        self.file.write("_test.ifc")


if __name__ == "__main__":
    unittest.main()
