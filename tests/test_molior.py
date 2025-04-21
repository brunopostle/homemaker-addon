#!/usr/bin/python3

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior import Wall, Molior
from molior.geometry import distance_2d


def test_wall_default_properties():
    wall = Wall()

    assert wall.height == 0.0
    wall.height = 3.0
    assert wall.height == 3.0

    assert wall.offset == -0.25
    wall.offset = -0.3
    assert wall.offset == -0.3


def test_wall_with_properties():
    wall2 = Wall({"height": 2.7, "offset": -0.4})
    assert wall2.height == 2.7
    assert wall2.offset == -0.4


def test_wall_geometry():
    wall3 = Wall(
        {
            "closed": False,
            "path": [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]],
            "extension": 0.25,
            "condition": "external",
            "normals": {"top": {}, "bottom": {}},
            "normal_set": "top",
        }
    )
    wall3.init_openings()
    assert len(wall3.path) == 3
    assert len(wall3.openings) == 2
    assert wall3.segments() == 2
    assert wall3.length_segment(0) == 5
    assert wall3.length_segment(1) == 50**0.5
    assert wall3.length_segment(2) == 125**0.5
    assert wall3.angle_segment(0) == 0.0
    assert wall3.angle_segment(1) == 45.0
    assert pytest.approx(wall3.angle_segment(2), abs=1e-7) == 206.5650512
    assert wall3.direction_segment(0) == [1, 0]
    assert wall3.normal_segment(0) == [0, -1]
    assert wall3.corner_coor(0) == [0, 0]
    assert wall3.corner_coor(1) == [5, 0]
    assert wall3.corner_coor(2) == [10, 5]
    assert wall3.corner_coor(3) == [0, 0]
    assert wall3.corner_coor(4) == [5, 0]
    assert wall3.corner_coor(5) == [10, 5]
    assert wall3.corner_coor(6) == [0, 0]
    assert wall3.corner_coor(-1) == [10, 5]
    assert wall3.corner_offset(0, 0.5) == [0, -0.5]
    assert wall3.corner_offset(0, -5) == [0, 5]
    assert wall3.corner_offset(1, 0.0) == [5, 0]
    assert pytest.approx(wall3.corner_offset(1, 5.0)[0], abs=1e-7) == 7.0710678
    assert pytest.approx(wall3.corner_offset(1, 5.0)[1], abs=1e-7) == -5.0
    assert wall3.corner_offset(2, 0.0) == [10, 5]
    assert pytest.approx(wall3.corner_in(0)[0], abs=1e-7) == 0
    assert pytest.approx(wall3.corner_in(0)[1], abs=1e-7) == 0.08
    assert wall3.corner_out(0) == [0, -0.25]
    assert wall3.extension_start() == [-0.25, 0.0]
    assert pytest.approx(distance_2d(wall3.extension_end(), [0, 0]), abs=1e-7) == 0.25


def test_wall_closed_path():
    wall4 = Wall(
        {
            "closed": True,
            "path": [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]],
            "normals": {"top": {}, "bottom": {}},
            "condition": "internal",
            "normal_set": "top",
        }
    )
    wall4.init_openings()
    assert len(wall4.path) == 3
    assert len(wall4.openings) == 3
    assert wall4.path[2] == [10.0, 5.0]
    assert wall4.segments() == 3

    wall4.populate_exterior_openings(2, "kitchen", 0)
    assert wall4.openings[2][0] == {
        "family": "kitchen outside window",
        "along": 0.5,
        "size": 0,
    }

    assert wall4.__dict__["guid"] == "my building"


def test_molior_defaults():
    molior = Molior()
    assert molior.share_dir == "share"
    assert Molior.style.get("default")["traces"]["exterior"]["condition"] == "external"
