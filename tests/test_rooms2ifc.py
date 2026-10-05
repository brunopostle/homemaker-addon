"""Tests for rooms2ifc.py, a rooms document file to an IFC file."""

import json
import os
import subprocess
import sys

import ifcopenshell

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DOCUMENT = {
    "format": "homemaker-rooms",
    "version": 1,
    "name": "rooms2ifc test",
    "meta": {"source": "ignored"},
    "rooms": [
        {
            "vertices": [[0, 0], [4, 0], [4, 3], [0, 3]],
            "elevation": 0.0,
            "height": 3.0,
            "stylename": "default",
            # the wall along vertex 3 -> 0 is a party wall
            "face_styles": [
                "default",
                "default",
                "default",
                "default",
                "default",
                "blank",
            ],
            "usage": "bedroom",
            "dom_id": "0/l",
            "code": "b1",
        },
        {
            "vertices": [[4, 0], [8, 0], [8, 3], [4, 3]],
            "elevation": 0.0,
            "height": 3.0,
            "usage": "kitchen",
        },
    ],
}


def run(*args):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "rooms2ifc.py"), *args],
        capture_output=True,
        text=True,
    )


def test_rooms2ifc(tmp_path):
    rooms_path = tmp_path / "test.rooms.json"
    ifc_path = tmp_path / "test.ifc"
    rooms_path.write_text(json.dumps(DOCUMENT))

    result = run(str(rooms_path), str(ifc_path))
    assert result.returncode == 0, result.stderr

    ifc = ifcopenshell.open(str(ifc_path))
    assert ifc.by_type("IfcBuilding")[0].Name == "rooms2ifc test"
    names = sorted(
        (space.Name or "").split("/")[0] for space in ifc.by_type("IfcSpace")
    )
    assert names == ["bedroom-space", "kitchen-space"], names
    assert ifc.by_type("IfcWall")
    assert ifc.by_type("IfcWindow")


def test_rooms2ifc_no_rooms(tmp_path):
    rooms_path = tmp_path / "empty.rooms.json"
    ifc_path = tmp_path / "empty.ifc"
    rooms_path.write_text(json.dumps({"rooms": []}))

    result = run(str(rooms_path), str(ifc_path))
    assert result.returncode != 0
    assert "no rooms" in result.stderr
    assert not ifc_path.exists()


def test_rooms2ifc_usage():
    result = run()
    assert result.returncode != 0
    assert "Usage:" in result.stderr
