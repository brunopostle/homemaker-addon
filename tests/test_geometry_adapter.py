"""Tests for web/geometry_adapter.py.

Key things verified:
- Three.js Y-up → IFC Z-up coordinate axis swap
- All n+2 faces generated per room (floor + ceiling + n walls)
- Widget centroid placed correctly in IFC space
- Per-face style assignment
- Direct faces_from_json / widgets_from_json paths
- _snap rounding
"""

import os
import sys

_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _repo)
sys.path.insert(0, os.path.join(_repo, "web"))

import pytest
from geometry_adapter import (
    faces_from_json,
    widgets_from_json,
    rooms_to_faces_and_widgets,
    _snap,
    _room,
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


def _quad(px=0, pz=0, w=4, d=4, elevation=0, height=3,
          stylename="default", usage="living", face_styles=None):
    """Build a rectangular quad-cell room dict (Three.js format)."""
    r = {
        "vertices":  [[px, pz], [px+w, pz], [px+w, pz+d], [px, pz+d]],
        "elevation": elevation,
        "height":    height,
        "stylename": stylename,
        "usage":     usage,
    }
    if face_styles is not None:
        r["face_styles"] = face_styles
    return r


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
            {"vertices": [[0, 0, 0], [1, 0, 0]]},    # only 2 points — skipped
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
            {"position": [0, 0], "usage": "kitchen"},   # too short — skipped
            {"position": [1, 2, 3], "usage": "kitchen"},
        ]
        widgets = widgets_from_json(widget_data)
        assert len(widgets) == 1


# ---------------------------------------------------------------------------
# rooms_to_faces_and_widgets — face count
# ---------------------------------------------------------------------------

class TestFaceCount:
    def test_quad_produces_six_faces(self):
        faces, widgets = rooms_to_faces_and_widgets([_quad()])
        assert len(faces) == 6     # floor + ceiling + 4 walls

    def test_quad_produces_one_widget(self):
        _, widgets = rooms_to_faces_and_widgets([_quad()])
        assert len(widgets) == 1

    def test_two_quads_produce_twelve_faces(self):
        rooms = [_quad(px=0), _quad(px=5)]
        faces, widgets = rooms_to_faces_and_widgets(rooms)
        assert len(faces) == 12
        assert len(widgets) == 2

    def test_triangle_produces_five_faces(self):
        tri = {
            "vertices": [[0, 0], [3, 0], [1.5, 3]],
            "elevation": 0, "height": 3,
            "stylename": "default", "usage": "living",
        }
        faces, _ = rooms_to_faces_and_widgets([tri])
        assert len(faces) == 5     # floor + ceiling + 3 walls

    def test_empty_rooms(self):
        faces, widgets = rooms_to_faces_and_widgets([])
        assert faces == []
        assert widgets == []


# ---------------------------------------------------------------------------
# Coordinate axis conversion
# ---------------------------------------------------------------------------

class TestCoordinateConversion:
    """
    Three.js: vertices are [[three_x, three_z], ...], elevation = Three.js Y
    IFC:      IFC X = three_x, IFC Y = three_z (depth), IFC Z = elevation
    """

    def test_ifc_z_equals_elevation(self):
        # elevation=5 → all IFC Z values start at 5 (floor), end at 8 (ceiling, h=3)
        faces, _ = rooms_to_faces_and_widgets([_quad(elevation=5, height=3)])
        all_z = [z for face in faces for (x, y, z) in _face_vertices(face)]
        assert min(all_z) == pytest.approx(5.0)
        assert max(all_z) == pytest.approx(8.0)

    def test_ifc_y_equals_three_z_depth(self):
        # vertices with three_z in [0, 4] → IFC Y in [0, 4]
        faces, _ = rooms_to_faces_and_widgets([_quad(pz=2, d=4)])
        all_y = [y for face in faces for (x, y, z) in _face_vertices(face)]
        assert min(all_y) == pytest.approx(2.0)
        assert max(all_y) == pytest.approx(6.0)

    def test_ifc_x_equals_three_x_unchanged(self):
        # vertices with three_x in [3, 7] → IFC X in [3, 7]
        faces, _ = rooms_to_faces_and_widgets([_quad(px=3, w=4)])
        all_x = [x for face in faces for (x, y, z) in _face_vertices(face)]
        assert min(all_x) == pytest.approx(3.0)
        assert max(all_x) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# Widget centroid
# ---------------------------------------------------------------------------

class TestWidgetCentroid:
    def test_centroid_at_room_centre(self):
        # quad at origin, 4×4×3 → IFC centroid (2, 2, 1.5)
        _, widgets = rooms_to_faces_and_widgets([_quad()])
        cx, cy, cz = _coords(widgets[0])
        assert cx == pytest.approx(2.0)
        assert cy == pytest.approx(2.0)
        assert cz == pytest.approx(1.5)

    def test_centroid_respects_elevation(self):
        _, widgets = rooms_to_faces_and_widgets([_quad(elevation=3, height=4)])
        _, _, cz = _coords(widgets[0])
        assert cz == pytest.approx(5.0)    # 3 + 4/2

    def test_widget_usage_preserved(self):
        _, widgets = rooms_to_faces_and_widgets([_quad(usage="bedroom")])
        assert widgets[0].Get("usage") == "bedroom"


# ---------------------------------------------------------------------------
# Face planes (axis-aligned geometry check)
# ---------------------------------------------------------------------------

class TestFacePlanes:
    def test_six_distinct_planes(self):
        # quad at px=1,pz=3, w=4,d=5, elevation=2, height=6
        # IFC X∈{1,5}, IFC Y∈{3,8}, IFC Z∈{2,8}
        faces, _ = rooms_to_faces_and_widgets([_quad(px=1, pz=3, w=4, d=5, elevation=2, height=6)])
        assert len(faces) == 6

        plane_xs, plane_ys, plane_zs = set(), set(), set()
        for face in faces:
            verts = _face_vertices(face)
            xs = {round(x, 6) for x, y, z in verts}
            ys = {round(y, 6) for x, y, z in verts}
            zs = {round(z, 6) for x, y, z in verts}
            if len(xs) == 1: plane_xs.add(next(iter(xs)))
            if len(ys) == 1: plane_ys.add(next(iter(ys)))
            if len(zs) == 1: plane_zs.add(next(iter(zs)))

        assert sorted(plane_xs) == pytest.approx([1.0, 5.0])
        assert sorted(plane_ys) == pytest.approx([3.0, 8.0])
        assert sorted(plane_zs) == pytest.approx([2.0, 8.0])


# ---------------------------------------------------------------------------
# Per-face styles
# ---------------------------------------------------------------------------

class TestPerFaceStyles:
    """face_styles: [0]=floor, [1]=ceiling, [2..5]=walls in vertex order."""

    def test_all_faces_get_explicit_style(self):
        styles = ["s0", "s1", "s2", "s3", "s4", "s5"]
        faces, _ = rooms_to_faces_and_widgets([_quad(face_styles=styles)])
        assert [f.Get("stylename") for f in faces] == styles

    def test_partial_face_styles_falls_back(self):
        faces, _ = rooms_to_faces_and_widgets([
            _quad(face_styles=["a", "b", "c"], stylename="default")
        ])
        assert faces[0].Get("stylename") == "a"
        assert faces[1].Get("stylename") == "b"
        assert faces[2].Get("stylename") == "c"
        assert faces[3].Get("stylename") == "default"

    def test_none_entry_falls_back_to_stylename(self):
        faces, _ = rooms_to_faces_and_widgets([
            _quad(face_styles=["marble", None, None, None, None, None], stylename="default")
        ])
        assert faces[0].Get("stylename") == "marble"
        assert all(f.Get("stylename") == "default" for f in faces[1:])

    def test_empty_face_styles_falls_back(self):
        faces, _ = rooms_to_faces_and_widgets([_quad(face_styles=[], stylename="fox")])
        assert all(f.Get("stylename") == "fox" for f in faces)

    def test_no_face_styles_falls_back(self):
        faces, _ = rooms_to_faces_and_widgets([_quad(stylename="fox")])
        assert all(f.Get("stylename") == "fox" for f in faces)

    def test_floor_style(self):
        faces, _ = rooms_to_faces_and_widgets([_quad(face_styles=["marble"] + [None]*5)])
        assert faces[0].Get("stylename") == "marble"

    def test_ceiling_style(self):
        faces, _ = rooms_to_faces_and_widgets([_quad(face_styles=[None, "fancy"] + [None]*4)])
        assert faces[1].Get("stylename") == "fancy"

    def test_wall_styles(self):
        faces, _ = rooms_to_faces_and_widgets([
            _quad(face_styles=[None, None, "brick", "brick", "brick", "brick"])
        ])
        for f in faces[2:]:
            assert f.Get("stylename") == "brick"

    def test_two_rooms_independent_styles(self):
        rooms = [_quad(face_styles=["a"]*6), _quad(px=5, face_styles=["b"]*6)]
        faces, _ = rooms_to_faces_and_widgets(rooms)
        assert all(f.Get("stylename") == "a" for f in faces[:6])
        assert all(f.Get("stylename") == "b" for f in faces[6:])
