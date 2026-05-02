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
    defaults = {"position": [0, 0, 0], "size": [4, 4, 3], "usage": "living", "stylename": "default"}
    return {**defaults, **kwargs}

def _quad(z=0):
    """A valid 4-vertex planar face (1 m square at given z)."""
    return {"vertices": [[0,0,z],[1,0,z],[1,1,z],[0,1,z]], "stylename": "default"}


# ---------------------------------------------------------------------------
# RoomData — position
# ---------------------------------------------------------------------------

class TestRoomPosition:
    def test_valid(self):
        RoomData(**_room(position=[0, 0, 0]))

    def test_too_few_coords(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            RoomData(**_room(position=[0, 0]))

    def test_too_many_coords(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            RoomData(**_room(position=[0, 0, 0, 0]))

    def test_coord_out_of_range_high(self):
        with pytest.raises(ValidationError, match="out of range"):
            RoomData(**_room(position=[0, 0, 20_000]))

    def test_coord_out_of_range_low(self):
        with pytest.raises(ValidationError, match="out of range"):
            RoomData(**_room(position=[-20_000, 0, 0]))

    def test_boundary_coord_accepted(self):
        RoomData(**_room(position=[9999.9, -9999.9, 0]))


# ---------------------------------------------------------------------------
# RoomData — size
# ---------------------------------------------------------------------------

class TestRoomSize:
    def test_valid(self):
        RoomData(**_room(size=[4, 4, 3]))

    def test_too_few_dims(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            RoomData(**_room(size=[4, 4]))

    def test_too_many_dims(self):
        with pytest.raises(ValidationError, match="exactly 3"):
            RoomData(**_room(size=[4, 4, 3, 1]))

    def test_zero_dimension(self):
        with pytest.raises(ValidationError, match="minimum"):
            RoomData(**_room(size=[0, 4, 3]))

    def test_negative_dimension(self):
        with pytest.raises(ValidationError, match="minimum"):
            RoomData(**_room(size=[-1, 4, 3]))

    def test_below_min_dim(self):
        with pytest.raises(ValidationError, match="minimum"):
            RoomData(**_room(size=[0.1, 4, 3]))

    def test_exactly_min_dim(self):
        RoomData(**_room(size=[0.3, 0.3, 0.3]))

    def test_above_max_dim(self):
        with pytest.raises(ValidationError, match="maximum"):
            RoomData(**_room(size=[4, 4, 2000]))

    def test_exactly_max_dim(self):
        RoomData(**_room(size=[1000, 1000, 1000]))


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
        with pytest.raises(ValidationError, match="at most 6"):
            RoomData(**_room(face_styles=["default"] * 7))

    def test_bad_style_in_list(self):
        with pytest.raises(ValidationError, match="alphanumeric"):
            RoomData(**_room(face_styles=["default", "../bad"]))

    def test_none_entry_accepted(self):
        RoomData(**_room(face_styles=["default", None, "foxhouse", None, None, None]))


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
