"""Tests for the structural analysis model of a generated building."""

import json
import os
import subprocess
import sys

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# two rooms over two rooms, this gets windows and an entrance door
DOCUMENT = {
    "format": "homemaker-rooms",
    "version": 1,
    "name": "structural test",
    "rooms": [
        {
            "vertices": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "living",
        },
        {
            "vertices": [[5, 0], [9, 0], [9, 4], [5, 4]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "kitchen",
        },
        {
            "vertices": [[0, 0], [5, 0], [5, 4], [0, 4]],
            "elevation": 3.0,
            "height": 3.0,
            "usage": "bedroom",
        },
        {
            "vertices": [[5, 0], [9, 0], [9, 4], [5, 4]],
            "elevation": 3.0,
            "height": 3.0,
            "usage": "bedroom",
        },
    ],
}


@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    path = tmp_path_factory.mktemp("structural")
    rooms_path = path / "test.rooms.json"
    ifc_path = path / "test.ifc"
    rooms_path.write_text(json.dumps(DOCUMENT))
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(ROOT, "rooms2ifc.py"),
            str(rooms_path),
            str(ifc_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return ifcopenshell.open(str(ifc_path))


def test_materials_have_stiffness(ifc):
    """an analysis has to be told the stiffness of every structural member"""
    members = ifc.by_type("IfcStructuralMember")
    assert members
    names = set()
    for member in members:
        for material in ifcopenshell.util.element.get_materials(member):
            names.add(material.Name)
            psets = ifcopenshell.util.element.get_psets(material)
            mechanical = psets["Pset_MaterialMechanical"]
            assert 1e9 < mechanical["YoungModulus"] < 1e11
            assert 0.0 < mechanical["PoissonRatio"] < 0.5
            assert psets["Pset_MaterialCommon"]["MassDensity"] > 0.0
    assert names == {"Concrete", "Masonry"}


def test_units_of_stiffness_and_density(ifc):
    """values in share/library.ifc are Pa and kg/m3, while forces are in kN"""
    assert ifcopenshell.util.unit.calculate_unit_scale(ifc, "FORCEUNIT") == 1000.0
    assert ifcopenshell.util.unit.calculate_unit_scale(ifc, "PRESSUREUNIT") == 1.0
    assert ifcopenshell.util.unit.get_project_unit(ifc, "PRESSUREUNIT").Name == "PASCAL"
    modulus = ifcopenshell.util.unit.get_project_unit(ifc, "MODULUSOFELASTICITYUNIT")
    assert [(element.Unit.Name, element.Exponent) for element in modulus.Elements] == [
        ("PASCAL", 1)
    ]
    density = ifcopenshell.util.unit.get_project_unit(ifc, "MASSDENSITYUNIT")
    assert {
        (element.Unit.UnitType, element.Unit.Prefix, element.Exponent)
        for element in density.Elements
    } == {("MASSUNIT", "KILO", 1), ("LENGTHUNIT", None, -3)}
