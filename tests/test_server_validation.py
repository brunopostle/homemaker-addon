"""Tests for server.py Pydantic input validation.

These tests do NOT start the FastAPI server or import topologic_core — they
exercise the model validators directly via model instantiation.  Pydantic
raises ValidationError on bad input, which FastAPI converts to HTTP 422.
"""

import os
import sys

_repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _repo)
sys.path.insert(0, os.path.join(_repo, "web"))

import pytest
from pydantic import ValidationError

# Import only the models — not the app startup code that loads molior.
from server import FaceData, WidgetData, RoomData, GenerateRequest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _room(**kwargs):
    """Build a valid quad room dict (4-vertex rectangle)."""
    defaults = {
        "vertices":  [[0, 0], [4, 0], [4, 4], [0, 4]],
        "elevation": 0.0,
        "height":    3.0,
        "stylename": "default",
        "usage":     "living",
    }
    return {**defaults, **kwargs}

def _quad(z=0):
    """A valid 4-vertex planar face (1 m square at given z)."""
    return {"vertices": [[0,0,z],[1,0,z],[1,1,z],[0,1,z]], "stylename": "default"}


# ---------------------------------------------------------------------------
# RoomData — vertices
# ---------------------------------------------------------------------------

class TestRoomVertices:
    def test_valid_quad(self):
        RoomData(**_room())

    def test_triangle_accepted(self):
        RoomData(**_room(vertices=[[0, 0], [3, 0], [1.5, 3]]))

    def test_too_few_vertices(self):
        with pytest.raises(ValidationError, match="at least 3"):
            RoomData(**_room(vertices=[[0, 0], [1, 0]]))

    def test_too_many_vertices(self):
        with pytest.raises(ValidationError, match="at most 64"):
            RoomData(**_room(vertices=[[float(i), 0] for i in range(65)]))

    def test_concave_rejected(self):
        with pytest.raises(ValidationError, match="convex"):
            RoomData(**_room(vertices=[[0, 0], [4, 0], [2, 1], [4, 4], [0, 4]]))

    def test_convex_pentagon_accepted(self):
        import math
        verts = [[math.cos(2*math.pi*i/5), math.sin(2*math.pi*i/5)] for i in range(5)]
        RoomData(**_room(vertices=verts))

    def test_vertex_out_of_range(self):
        with pytest.raises(ValidationError, match="out of range"):
            RoomData(**_room(vertices=[[0, 0], [4, 0], [4, 20_000]]))

    def test_vertex_wrong_dimension(self):
        with pytest.raises(ValidationError, match="exactly 2"):
            RoomData(**_room(vertices=[[0, 0, 0], [4, 0, 0], [4, 4, 0]]))

    def test_boundary_coords_accepted(self):
        RoomData(**_room(vertices=[[-9999.9, -9999.9], [9999.9, -9999.9], [9999.9, 9999.9], [-9999.9, 9999.9]]))

    def test_collinear_polygon_rejected(self):
        # All three points on a line — passes convexity but has zero area.
        with pytest.raises(ValidationError, match="area"):
            RoomData(**_room(vertices=[[0, 0], [1, 0], [2, 0]]))


# ---------------------------------------------------------------------------
# RoomData — height
# ---------------------------------------------------------------------------

class TestRoomHeight:
    def test_valid(self):
        RoomData(**_room(height=3.0))

    def test_too_small(self):
        with pytest.raises(ValidationError, match="minimum"):
            RoomData(**_room(height=0.1))

    def test_at_min(self):
        RoomData(**_room(height=0.3))

    def test_too_large(self):
        with pytest.raises(ValidationError, match="maximum"):
            RoomData(**_room(height=2000))

    def test_at_max(self):
        RoomData(**_room(height=1000))

    def test_zero_rejected(self):
        with pytest.raises(ValidationError, match="minimum"):
            RoomData(**_room(height=0.0))


# ---------------------------------------------------------------------------
# RoomData — elevation
# ---------------------------------------------------------------------------

class TestRoomElevation:
    def test_valid_zero(self):
        RoomData(**_room(elevation=0.0))

    def test_negative_ok(self):
        RoomData(**_room(elevation=-100.0))

    def test_out_of_range_high(self):
        with pytest.raises(ValidationError, match="out of range"):
            RoomData(**_room(elevation=20_000))

    def test_out_of_range_low(self):
        with pytest.raises(ValidationError, match="out of range"):
            RoomData(**_room(elevation=-20_000))

    def test_boundary_accepted(self):
        RoomData(**_room(elevation=9999.9))


# ---------------------------------------------------------------------------
# RoomData — stylename
# ---------------------------------------------------------------------------

class TestRoomStylename:
    def test_valid(self):
        RoomData(**_room(stylename="foxhouse"))

    def test_valid_with_hyphen_and_underscore(self):
        RoomData(**_room(stylename="my-style_v2"))

    def test_path_traversal(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(stylename="../../../etc/passwd"))

    def test_slash_rejected(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(stylename="a/b"))

    def test_dot_rejected(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(stylename="a.b"))

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(stylename=""))

    def test_too_long(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(stylename="a" * 65))


# ---------------------------------------------------------------------------
# RoomData — usage
# ---------------------------------------------------------------------------

class TestRoomUsage:
    @pytest.mark.parametrize("u", ["living", "bedroom", "kitchen", "circulation",
                                   "toilet", "stair", "void", "outside"])
    def test_valid_usages(self, u):
        RoomData(**_room(usage=u))

    def test_invalid_usage(self):
        with pytest.raises(ValidationError, match="usage must be one of"):
            RoomData(**_room(usage="garage"))

    def test_empty_usage(self):
        with pytest.raises(ValidationError, match="usage must be one of"):
            RoomData(**_room(usage=""))


# ---------------------------------------------------------------------------
# RoomData — face_styles
# ---------------------------------------------------------------------------

class TestRoomFaceStyles:
    def test_none_accepted(self):
        RoomData(**_room(face_styles=None))

    def test_six_valid(self):
        RoomData(**_room(face_styles=["default"] * 6))

    def test_fewer_than_six_accepted(self):
        RoomData(**_room(face_styles=["default", "foxhouse"]))

    def test_too_many_rejected(self):
        # 4-vertex quad: max face_styles = 4+2 = 6; 7 should be rejected
        with pytest.raises(ValidationError, match="at most 6"):
            RoomData(**_room(face_styles=["default"] * 7))

    def test_bad_style_in_list(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(face_styles=["default", "../bad"]))

    def test_none_entry_accepted(self):
        RoomData(**_room(face_styles=["default", None, "foxhouse", None, None, None]))

    def test_triangle_room_max_five(self):
        # 3-vertex triangle: max face_styles = 3+2 = 5; 6 should be rejected
        with pytest.raises(ValidationError, match="at most 5"):
            RoomData(**_room(vertices=[[0,0],[3,0],[1.5,3]], face_styles=["default"] * 6))

    def test_triangle_room_five_accepted(self):
        RoomData(**_room(vertices=[[0,0],[3,0],[1.5,3]], face_styles=["default"] * 5))


# ---------------------------------------------------------------------------
# FaceData — vertices
# ---------------------------------------------------------------------------

class TestFaceData:
    def test_valid_quad(self):
        FaceData(**_quad())

    def test_triangle_rejected(self):
        with pytest.raises(ValidationError, match="exactly 4"):
            FaceData(vertices=[[0,0,0],[1,0,0],[0,1,0]], stylename="default")

    def test_five_vertices_rejected(self):
        with pytest.raises(ValidationError, match="exactly 4"):
            FaceData(vertices=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0.5,0]], stylename="default")

    def test_vertex_missing_coord(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            FaceData(vertices=[[0,0],[1,0,0],[1,1,0],[0,1,0]], stylename="default")

    def test_short_edge_rejected(self):
        with pytest.raises(ValidationError, match="minimum"):
            # First edge nearly zero length
            FaceData(vertices=[[0,0,0],[0.001,0,0],[1,1,0],[0,1,0]], stylename="default")

    def test_vertex_out_of_range(self):
        with pytest.raises(ValidationError, match="out of range"):
            FaceData(vertices=[[0,0,0],[1,0,0],[1,1,0],[0,50_000,0]], stylename="default")

    def test_bad_stylename(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            FaceData(vertices=[[0,0,0],[1,0,0],[1,1,0],[0,1,0]], stylename="../bad")


# ---------------------------------------------------------------------------
# WidgetData
# ---------------------------------------------------------------------------

class TestWidgetData:
    def test_valid(self):
        WidgetData(position=[1, 2, 3], usage="bedroom")

    def test_position_too_short(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            WidgetData(position=[1, 2], usage="living")

    def test_position_out_of_range(self):
        with pytest.raises(ValidationError, match="out of range"):
            WidgetData(position=[0, 0, 99_999], usage="living")

    def test_invalid_usage(self):
        with pytest.raises(ValidationError, match="usage must be one of"):
            WidgetData(position=[1, 2, 3], usage="warehouse")


# ---------------------------------------------------------------------------
# GenerateRequest — top-level
# ---------------------------------------------------------------------------

class TestGenerateRequest:
    def test_rooms_path(self):
        GenerateRequest(rooms=[_room()])

    def test_faces_path(self):
        GenerateRequest(faces=[_quad()])

    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="provide either"):
            GenerateRequest(name="test")

    def test_both_rooms_and_faces_rejected(self):
        with pytest.raises(ValidationError, match="not both"):
            GenerateRequest(rooms=[_room()], faces=[_quad()])

    def test_name_too_long(self):
        with pytest.raises(ValidationError, match="256"):
            GenerateRequest(rooms=[_room()], name="x" * 257)

    def test_name_exactly_256(self):
        GenerateRequest(rooms=[_room()], name="x" * 256)

    def test_too_many_rooms(self):
        with pytest.raises(ValidationError, match="too many rooms"):
            GenerateRequest(rooms=[_room()] * 501)

    def test_500_rooms_accepted(self):
        GenerateRequest(rooms=[_room()] * 500)

    def test_too_many_faces(self):
        with pytest.raises(ValidationError, match="too many faces"):
            GenerateRequest(faces=[_quad(z=float(i) * 2) for i in range(5001)])

    def test_5000_faces_accepted(self):
        GenerateRequest(faces=[_quad(z=float(i) * 2) for i in range(5000)])
