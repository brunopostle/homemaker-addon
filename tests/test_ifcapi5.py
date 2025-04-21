#!/usr/bin/python3

import os
import sys
import pytest
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.root

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

api = ifcopenshell.api


@pytest.fixture
def ifc_file():
    file = molior.ifc.init(name="My Project")
    body_context = get_context_by_name(file, context_identifier="Body")

    project = file.by_type("IfcProject")[0]

    site = get_site_by_name(file, project, "My Site")
    building = get_building_by_name(file, site, "My Building")
    assert len(file.by_type("IfcBuilding")) == 1

    get_site_by_name(file, project, "My Site")
    get_building_by_name(file, site, "My Building")
    assert len(file.by_type("IfcSite")) == 1
    assert len(file.by_type("IfcBuilding")) == 1

    get_building_by_name(file, site, "My Other Building")
    assert len(file.by_type("IfcSite")) == 1
    assert len(file.by_type("IfcBuilding")) == 2

    site2 = get_site_by_name(file, project, "My Other Site")
    assert len(file.by_type("IfcSite")) == 2
    get_building_by_name(file, site2, "My Building")
    assert len(file.by_type("IfcBuilding")) == 3

    model1 = get_structural_analysis_model_by_name(file, building, "My Model")
    get_structural_analysis_model_by_name(file, building, "My Model")
    model2 = get_structural_analysis_model_by_name(file, building, "My Model")
    assert len(file.by_type("IfcStructuralAnalysisModel")) == 1
    assert model1 == model2

    create_storeys(file, building, {0.0: 0})

    return {"file": file, "body_context": body_context}


def test_import_material(ifc_file):
    file = ifc_file["file"]

    # retrieve a material from an IFC library
    mystyle = Style()
    (stylename, library_file, element) = mystyle.get_from_library(
        "courtyard", "IfcMaterial", "Screed"
    )
    # add to current project
    local_element = api.project.append_asset(
        file, library=library_file, element=element
    )

    # create a library in this project
    library = get_library_by_name(file, stylename)
    # this doesn't work because an IFC Material isn't an Object Definition
    # so it doesn't HasContext and can't fit in a Project Library :(
    api.project.assign_declaration(
        file,
        definitions=[local_element],
        relating_context=library,
    )

    # all in one method
    get_material_by_name(file, mystyle, stylename="courtyard", name="Concrete")

    file.write("_test.ifc")


def test_import_door(ifc_file):
    file = ifc_file["file"]
    body_context = ifc_file["body_context"]

    mystyle = Style()

    (stylename, library_file, element) = mystyle.get_from_library(
        "arcade", "IfcWIndowType", "arch_194x300"
    )
    # add to current project
    local_element = api.project.append_asset(
        file, library=library_file, element=element
    )
    for representation_map in local_element.RepresentationMaps:
        if (
            representation_map.MappedRepresentation.RepresentationIdentifier
            == "Clearance"
        ):
            myopening = api.root.create_entity(
                file,
                ifc_class="IfcOpeningElement",
                name=local_element.Name,
                predefined_type="OPENING",
            )
            api.geometry.assign_representation(
                file,
                product=myopening,
                representation=file.createIfcShapeRepresentation(
                    body_context,
                    body_context.ContextIdentifier,
                    representation_map.MappedRepresentation.RepresentationType,
                    representation_map.MappedRepresentation.Items,
                ),
            )

    file.write("_test.ifc")
