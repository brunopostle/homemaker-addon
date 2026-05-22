#!/usr/bin/python3
"""Integration test: build a full IFC model from a realistic multi-room CellComplex.
Uses the setup_cell_complex fixture from conftest.py."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from molior import Molior


def test_molior(setup_cell_complex):
    cc, circulation, _ = setup_cell_complex
    traces, normals, elevations = cc.GetTraces()
    hulls = cc.GetHulls()

    molior_object = Molior(
        circulation=circulation,
        traces=traces,
        hulls=hulls,
        normals=normals,
        cellcomplex=cc,
        name="My test building",
        elevations=elevations,
    )
    molior_object.execute()
    molior_object.file.write("_test.ifc")
