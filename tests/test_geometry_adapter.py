"""Tests for web/geometry_adapter.py.

Key things verified:
- Three.js Y-up → IFC Z-up coordinate axis swap
- All 6 faces generated per room (including ceiling/floor)
- Face normals / vertex winding produce planar faces
- Widget centroid placed in IFC space
- Direct faces_from_json / widgets_from_json paths
- _snap rounding
"""

import os
import sys

# Make the repo root importable (topologist, molior) and web/ (geometry_adapter).
_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _repo)
sys.path.insert(0, os.path.join(_repo, "web"))

import pytest
from geometry_adapter import (
    faces_from_json,
    widgets_from_json,
    rooms_to_faces_and_widgets,
    _snap,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _coords(vertex):
    """Return (x, y, z) from a topologic_core Vertex."""
    return (vertex.X(), vertex.Y(), vertex.Z())


def _face_vertices(face):
    """Return list of (x,y,z) tuples for a topologic_core Face."""
    verts = []
    face.Vertices(None, verts)
    return [_coords(v) for v in verts]


# ---------------------------------------------------------------------------
# _snap
# ---------------------------------------------------------------------------

class TestSnap:
    def test_rounds_to_3dp(self):
        assert _snap([1.23456789, 0.0, -2.99999]) == [1.235, 0.0, -3.0]

    def test_handles_integers(self):
        assert _snap([1, 2, 3]) == [1.0, 2.0, 3.0]

    def test_handles_strings(self):
        assert _snap(["1.5", "2.5", "3.5"]) == [1.5, 2.5, 3.5]


# ---------------------------------------------------------------------------
# faces_from_json
# ---------------------------------------------------------------------------

class TestFacesFromJson:
    def test_basic_face(self):
        face_data = [
            {
                "vertices": [[0, 0, 0], [5, 0, 0], [5, 0, 3], [0, 0, 3]],
                "stylename": "brick",
            }
        ]
        faces = faces_from_json(face_data)
        assert len(faces) == 1
        assert faces[0].Get("stylename") == "brick"

    def test_default_stylename(self):
        face_data = [{"vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0]]}]
        faces = faces_from_json(face_data)
        assert faces[0].Get("stylename") == "default"

    def test_skips_degenerate_faces(self):
        face_data = [
            {"vertices": [[0, 0, 0], [1, 0, 0]]},  # only 2 points — skipped
            {"vertices": [[0, 0, 0], [2, 0, 0], [2, 2, 0]]},  # valid
        ]
        faces = faces_from_json(face_data)
        assert len(faces) == 1

    def test_empty_list(self):
        assert faces_from_json([]) == []


# ---------------------------------------------------------------------------
# widgets_from_json
# ---------------------------------------------------------------------------

class TestWidgetsFromJson:
    def test_basic_widget(self):
        widget_data = [{"position": [1.0, 2.0, 3.0], "usage": "bedroom"}]
        widgets = widgets_from_json(widget_data)
        assert len(widgets) == 1
        assert widgets[0].Get("usage") == "bedroom"
        assert _coords(widgets[0]) == pytest.approx((1.0, 2.0, 3.0))

    def test_default_usage(self):
        widget_data = [{"position": [0, 0, 1]}]
        widgets = widgets_from_json(widget_data)
        assert widgets[0].Get("usage") == "living"

    def test_skips_short_position(self):
        widget_data = [
            {"position": [0, 0], "usage": "kitchen"},  # too short — skipped
            {"position": [1, 2, 3], "usage": "kitchen"},
        ]
        widgets = widgets_from_json(widget_data)
        assert len(widgets) == 1


# ---------------------------------------------------------------------------
# rooms_to_faces_and_widgets — face count
# ---------------------------------------------------------------------------

class TestRoomsToFacesAndWidgets:
    def _simple_room(self, px=0, py=0, pz=0, w=4, d=3, h=3,
                     stylename="default", usage="living"):
        # Three.js position: px=east, py=elevation, pz=depth
        return {
            "position": [px, py, pz],
            "size": [w, d, h],
            "stylename": stylename,
            "usage": usage,
        }

    def test_one_room_produces_six_faces(self):
        faces, widgets = rooms_to_faces_and_widgets([self._simple_room()])
        assert len(faces) == 6

    def test_one_room_produces_one_widget(self):
        faces, widgets = rooms_to_faces_and_widgets([self._simple_room()])
        assert len(widgets) == 1

    def test_two_rooms_produce_twelve_faces(self):
        rooms = [self._simple_room(px=0), self._simple_room(px=4)]
        faces, widgets = rooms_to_faces_and_widgets(rooms)
        assert len(faces) == 12
        assert len(widgets) == 2

    def test_empty_rooms(self):
        faces, widgets = rooms_to_faces_and_widgets([])
        assert faces == []
        assert widgets == []


# ---------------------------------------------------------------------------
# rooms_to_faces_and_widgets — coordinate axis swap
# ---------------------------------------------------------------------------

class TestCoordinateSwap:
    """
    Three.js: position=[px, py, pz] where py=elevation (Y-up)
    IFC:      Z is elevation

    A room at Three.js position [1, 5, 2] (east=1, elevation=5, depth=2)
    should have its floor vertices at IFC Z=5, IFC Y=2.
    """

    def test_ifc_z_equals_three_js_y_elevation(self):
        room = {
            "position": [0.0, 5.0, 0.0],  # Three.js: elevated by 5 on Y axis
            "size": [4.0, 3.0, 3.0],
            "stylename": "default",
            "usage": "living",
        }
        faces, widgets = rooms_to_faces_and_widgets([room])
        all_z = [z for face in faces for (x, y, z) in _face_vertices(face)]
        # Floor vertices should be at IFC Z=5, ceiling at IFC Z=8
        assert min(all_z) == pytest.approx(5.0)
        assert max(all_z) == pytest.approx(8.0)

    def test_ifc_y_equals_three_js_z_depth(self):
        room = {
            "position": [0.0, 0.0, 7.0],  # Three.js: depth 7 on Z axis
            "size": [4.0, 3.0, 3.0],
            "stylename": "default",
            "usage": "living",
        }
        faces, widgets = rooms_to_faces_and_widgets([room])
        all_y = [y for face in faces for (x, y, z) in _face_vertices(face)]
        assert min(all_y) == pytest.approx(7.0)
        assert max(all_y) == pytest.approx(10.0)

    def test_ifc_x_unchanged(self):
        room = {
            "position": [3.0, 0.0, 0.0],  # Three.js: east by 3 on X axis
            "size": [4.0, 3.0, 3.0],
            "stylename": "default",
            "usage": "living",
        }
        faces, widgets = rooms_to_faces_and_widgets([room])
        all_x = [x for face in faces for (x, y, z) in _face_vertices(face)]
        assert min(all_x) == pytest.approx(3.0)
        assert max(all_x) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# rooms_to_faces_and_widgets — widget centroid
# ---------------------------------------------------------------------------

class TestWidgetCentroid:
    def test_centroid_at_room_centre_ifc_space(self):
        # Three.js position [0, 0, 0], size [4, 3, 3]
        # IFC space: px=0 py=0 pz=0, w=4 d=3 h=3
        # Centroid: IFC (2, 1.5, 1.5)
        room = {
            "position": [0.0, 0.0, 0.0],
            "size": [4.0, 3.0, 3.0],
            "stylename": "default",
            "usage": "bedroom",
        }
        _, widgets = rooms_to_faces_and_widgets([room])
        cx, cy, cz = _coords(widgets[0])
        assert cx == pytest.approx(2.0)
        assert cy == pytest.approx(1.5)
        assert cz == pytest.approx(1.5)

    def test_centroid_respects_elevation(self):
        # Three.js position [0, 3, 0]: elevated 3 on Y, so IFC Z starts at 3
        room = {
            "position": [0.0, 3.0, 0.0],
            "size": [4.0, 4.0, 3.0],
            "stylename": "default",
            "usage": "kitchen",
        }
        _, widgets = rooms_to_faces_and_widgets([room])
        cx, cy, cz = _coords(widgets[0])
        assert cz == pytest.approx(4.5)   # pz=3 + h/2=1.5

    def test_widget_usage_preserved(self):
        room = {
            "position": [0.0, 0.0, 0.0],
            "size": [4.0, 4.0, 3.0],
            "stylename": "default",
            "usage": "bathroom",
        }
        _, widgets = rooms_to_faces_and_widgets([room])
        assert widgets[0].Get("usage") == "bathroom"


# ---------------------------------------------------------------------------
# rooms_to_faces_and_widgets — face planes
# ---------------------------------------------------------------------------

class TestFacePlanes:
    """Each of the 6 generated faces should be axis-aligned and have distinct
    constant-coordinate values corresponding to the 6 sides of the cuboid."""

    def test_six_distinct_planes(self):
        room = {
            "position": [1.0, 2.0, 3.0],   # Three.js: east=1, elev=2, depth=3
            "size": [4.0, 5.0, 6.0],        # w=4, d=5, h=6
            "stylename": "default",
            "usage": "living",
        }
        faces, _ = rooms_to_faces_and_widgets([room])
        assert len(faces) == 6

        # IFC space: px=1, py=3, pz=2, qx=5, qy=8, qz=8
        # Expected constant planes: X∈{1,5}, Y∈{3,8}, Z∈{2,8}
        plane_xs = set()
        plane_ys = set()
        plane_zs = set()
        for face in faces:
            verts = _face_vertices(face)
            xs = {round(x, 6) for x, y, z in verts}
            ys = {round(y, 6) for x, y, z in verts}
            zs = {round(z, 6) for x, y, z in verts}
            if len(xs) == 1:
                plane_xs.add(next(iter(xs)))
            if len(ys) == 1:
                plane_ys.add(next(iter(ys)))
            if len(zs) == 1:
                plane_zs.add(next(iter(zs)))

        assert sorted(plane_xs) == pytest.approx([1.0, 5.0])
        assert sorted(plane_ys) == pytest.approx([3.0, 8.0])
        assert sorted(plane_zs) == pytest.approx([2.0, 8.0])

    def test_stylename_on_all_faces(self):
        room = {
            "position": [0, 0, 0],
            "size": [4, 4, 3],
            "stylename": "brick",
            "usage": "living",
        }
        faces, _ = rooms_to_faces_and_widgets([room])
        assert all(f.Get("stylename") == "brick" for f in faces)
