"""The 'utility' usage: laundries, plant and store rooms.

Added 2026-10-05 for homemaker-layout's programmes, which declare a `utility`
access class on 18 rooms that had no homemaker-addon counterpart (unmapped,
AllocateCells silently made them 'living'). Behaviour agreed with the owner:
kitchen-style windows, an outside door where there is access, reachable from
neighbouring rooms like a kitchen (no bedroom/toilet door rule), and not a
private usage for the intimacy gradient.
"""

import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "web"))

from molior import Molior  # noqa: E402
from molior.wall import Wall  # noqa: E402
from geometry_adapter import rooms_to_faces_and_widgets  # noqa: E402

ROOMS = [
    {
        "vertices": [[0, 0], [4, 0], [4, 3], [0, 3]],
        "elevation": 0.0,
        "height": 3.0,
        "usage": "utility",
    },
    {
        "vertices": [[4, 0], [8, 0], [8, 3], [4, 3]],
        "elevation": 0.0,
        "height": 3.0,
        "usage": "kitchen",
    },
]


@pytest.fixture(scope="module")
def ifc():
    faces, widgets = rooms_to_faces_and_widgets(ROOMS)
    m = Molior.from_faces_and_widgets(
        faces=faces,
        widgets=widgets,
        name="utility test",
        share_dir=os.path.join(ROOT, "share"),
    )
    m.execute()
    return m.file


def test_a_utility_room_becomes_a_utility_space(ifc):
    names = [s.Name or "" for s in ifc.by_type("IfcSpace")]
    assert any(n.startswith("utility") for n in names), names
    assert any(n.startswith("kitchen") for n in names), names


def test_a_utility_room_gets_its_own_floor_covering(ifc):
    types = [t.Name for t in ifc.by_type("IfcCoveringType")]
    assert "utility-floor" in types, types


def test_utility_windows_are_kitchen_style_and_it_may_have_an_outside_door():
    fake = SimpleNamespace(openings=[[]], level=0)
    Wall.populate_exterior_openings(fake, 0, "utility", 1)
    families = [o["family"] for o in fake.openings[0]]
    assert "kitchen outside window" in families
    assert "living outside door" in families
