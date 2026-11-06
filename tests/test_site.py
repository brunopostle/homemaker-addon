"""Tests for the location of the IfcSite."""

import json
import os
import subprocess
import sys

import ifcopenshell
import pytest
from ifcopenshell.util.geolocation import dms2dd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import molior.ifc
from molior.ifc import compound_angle, get_site_by_name
from molior.rooms import site_from_json


def location(site):
    return (
        dms2dd(*site.RefLatitude) if site.RefLatitude else None,
        dms2dd(*site.RefLongitude) if site.RefLongitude else None,
        site.RefElevation,
    )


@pytest.fixture
def ifc():
    return molior.ifc.init(name="My Project")


def test_default_site_is_in_sheffield(ifc):
    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site")
    assert site.RefLatitude == (53, 23, 0, 0)
    # west of Greenwich
    assert site.RefLongitude == (-1, -28, 0, 0)
    assert site.RefElevation == 75.0


def test_compound_angle():
    assert compound_angle(0.0) == [0, 0, 0, 0]
    assert compound_angle(53 + 23 / 60) == [53, 23, 0, 0]
    # all parts have the same sign
    assert compound_angle(-0.5) == [0, -30, 0, 0]
    assert compound_angle(-(10 + 1 / 3600 + 0.25 / 3600)) == [-10, 0, -1, -250000]
    # rounds up into the next degree, not to a million microseconds
    assert compound_angle(0.9999999999) == [1, 0, 0, 0]
    assert compound_angle(-179.99999999999) == [-180, 0, 0, 0]


def test_site_location(ifc):
    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(
        ifc, project, "My Site", latitude=-33.8568, longitude=151.2153, elevation=4.0
    )
    assert location(site) == pytest.approx((-33.8568, 151.2153, 4.0), abs=1e-6)
    assert all(isinstance(part, int) for part in site.RefLatitude)


def test_site_without_elevation_has_none(ifc):
    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site", latitude=10.0, longitude=20.0)
    assert location(site) == pytest.approx((10.0, 20.0, None), abs=1e-6)


def test_existing_site_is_moved_only_when_given_a_location(ifc):
    project = ifc.by_type("IfcProject")[0]
    site = get_site_by_name(ifc, project, "My Site", latitude=10.0, longitude=20.0)
    assert get_site_by_name(ifc, project, "My Site") == site
    assert location(site)[0:2] == pytest.approx((10.0, 20.0), abs=1e-6)
    assert get_site_by_name(ifc, project, "My Site", elevation=12.0) == site
    assert location(site) == pytest.approx((10.0, 20.0, 12.0), abs=1e-6)
    assert len(ifc.by_type("IfcSite")) == 1


def test_site_from_json():
    assert site_from_json(None) is None
    assert site_from_json({}) is None
    assert site_from_json({"latitude": None}) is None
    assert site_from_json({"latitude": 51, "longitude": -0.5}) == {
        "latitude": 51.0,
        "longitude": -0.5,
    }
    for wrong in (
        {"latitude": 91.0},
        {"longitude": -180.5},
        {"latitude": "53N"},
        {"latitude": True},
        {"altitude": 10.0},
    ):
        with pytest.raises(ValueError):
            site_from_json(wrong)


def test_rooms2ifc_site(tmp_path):
    document = {
        "site": {"latitude": 51.5072, "longitude": -0.1276, "elevation": 11.0},
        "rooms": [
            {
                "vertices": [[0, 0], [4, 0], [4, 3], [0, 3]],
                "elevation": 0.0,
                "height": 3.0,
                "usage": "living",
            }
        ],
    }
    rooms_path = tmp_path / "site.json"
    ifc_path = tmp_path / "site.ifc"
    rooms_path.write_text(json.dumps(document))
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "rooms2ifc.py"), rooms_path, ifc_path],
        check=True,
        capture_output=True,
    )
    ifc = ifcopenshell.open(ifc_path)
    (site,) = ifc.by_type("IfcSite")
    assert location(site) == pytest.approx((51.5072, -0.1276, 11.0), abs=1e-6)
