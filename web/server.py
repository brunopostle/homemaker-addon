"""homemaker-web FastAPI server.

Wraps the homemaker-addon Python library to expose IFC generation over HTTP.
The heavy lifting (topologic_core, ifcopenshell) runs server-side; the
browser receives a binary IFC file and renders it with @thatopen/components.

Style / usage terminology
-------------------------
share_dir   — server-side filesystem path to the share/ directory tree.
              Contains all style definitions. Never client-controlled.
stylename   — short leaf-directory name within share_dir (e.g. "default",
              "foxhouse", "simple"). Set per face/room by the client.
usage       — room type string ("bedroom", "kitchen", "living", …).
              Set per room (widget vertex) by the client.
"""

import os
import sys
import re
import math
import pathlib
import tempfile
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Annotated

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator, model_validator

# Both the web/ directory and repo root need to be on sys.path.
# web/ for geometry_adapter; repo root for molior/, topologist/.
_here = pathlib.Path(__file__).parent       # .../web/
_repo_root = _here.parent                   # .../homemaker-addon/
for _p in (str(_here), str(_repo_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from molior import Molior
import molior.ifc as molior_ifc
from geometry_adapter import faces_from_json, widgets_from_json, rooms_to_faces_and_widgets

# Locate share/ — works both from a git clone and from a pip-installed package.
# Override via SHARE_DIR env var for Docker deployments.
def _find_share_dir() -> str:
    try:
        import importlib.resources
        # molior lives at <root>/molior/, so .parent is <root>/
        candidate = str(importlib.resources.files("molior").parent / "share")
        if pathlib.Path(candidate).is_dir():
            return candidate
    except Exception:
        pass
    return str(_repo_root / "share")

_share_dir = os.environ.get("SHARE_DIR", _find_share_dir())

# One worker process per CPU for CPU-bound topologic_core work.
_executor = ProcessPoolExecutor(max_workers=2)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    _executor.shutdown(wait=False)

app = FastAPI(title="homemaker-web", version="0.1.0", lifespan=_lifespan)


# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

# stylename is used as a subdirectory name inside share/ — no path traversal allowed.
# usage is stored as a topologic attribute string — keep it simple.
_SIMPLE_RE  = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')
_VALID_USAGES = frozenset({
    "living", "bedroom", "kitchen", "circulation",
    "toilet", "stair", "void", "outside",
})
_COORD_RANGE = (-10_000.0, 10_000.0)    # metres — sane building envelope
_MIN_DIM     = 0.3                       # metres — mirrors editor MIN_DIM
_MAX_DIM     = 1_000.0                   # metres
_MIN_EDGE    = 0.01                      # metres — shortest face edge (raw faces)
_MAX_EDGE    = 2_000.0                   # metres — longest face edge (raw faces)
_MAX_ROOMS   = 500
_MAX_FACES   = 5_000


def _check_style(v: str, field: str = "stylename") -> str:
    if not _SIMPLE_RE.match(v):
        raise ValueError(f"{field} must be 1-64 alphanumeric/underscore/hyphen chars")
    return v


def _check_coords(coords: list[float], n: int, label: str) -> list[float]:
    if len(coords) != n:
        raise ValueError(f"{label} must have exactly {n} elements, got {len(coords)}")
    lo, hi = _COORD_RANGE
    for c in coords:
        if not (lo <= c <= hi):
            raise ValueError(f"{label} coordinate {c} out of range [{lo}, {hi}]")
    return coords


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FaceData(BaseModel):
    vertices: list[list[float]]
    stylename: str = "default"

    @field_validator("stylename")
    @classmethod
    def val_stylename(cls, v): return _check_style(v)

    @field_validator("vertices")
    @classmethod
    def val_vertices(cls, v):
        if len(v) != 4:
            raise ValueError(f"face must have exactly 4 vertices, got {len(v)}")
        for i, vert in enumerate(v):
            _check_coords(vert, 3, f"vertex {i}")
        # Check edge lengths — too-short edges collapse in topologic.
        for i in range(4):
            a, b = v[i], v[(i + 1) % 4]
            length = math.sqrt(sum((a[j] - b[j]) ** 2 for j in range(3)))
            if length < _MIN_EDGE:
                raise ValueError(
                    f"edge {i}-{(i+1)%4} length {length:.4f} m is below minimum {_MIN_EDGE} m"
                )
            if length > _MAX_EDGE:
                raise ValueError(
                    f"edge {i}-{(i+1)%4} length {length:.1f} m exceeds maximum {_MAX_EDGE} m"
                )
        return v


class WidgetData(BaseModel):
    position: list[float]
    usage: str = "living"

    @field_validator("position")
    @classmethod
    def val_position(cls, v): return _check_coords(v, 3, "position")

    @field_validator("usage")
    @classmethod
    def val_usage(cls, v):
        if v not in _VALID_USAGES:
            raise ValueError(f"usage must be one of {sorted(_VALID_USAGES)}")
        return v


class RoomData(BaseModel):
    position:    list[float]            # [px, py, pz] — Three.js Y-up coords
    size:        list[float]            # [w, d, h]
    face_styles: Optional[list[Optional[str]]] = None  # per-face stylenames, length ≤ 6; None entries fall back to stylename
    stylename:   str = "default"        # fallback when face_styles absent/short
    usage:       str = "living"

    @field_validator("position")
    @classmethod
    def val_position(cls, v): return _check_coords(v, 3, "position")

    @field_validator("size")
    @classmethod
    def val_size(cls, v):
        if len(v) != 3:
            raise ValueError(f"size must have exactly 3 elements, got {len(v)}")
        for dim in v:
            if dim < _MIN_DIM:
                raise ValueError(f"size dimension {dim} m is below minimum {_MIN_DIM} m")
            if dim > _MAX_DIM:
                raise ValueError(f"size dimension {dim} m exceeds maximum {_MAX_DIM} m")
        return v

    @field_validator("stylename")
    @classmethod
    def val_stylename(cls, v): return _check_style(v)

    @field_validator("usage")
    @classmethod
    def val_usage(cls, v):
        if v not in _VALID_USAGES:
            raise ValueError(f"usage must be one of {sorted(_VALID_USAGES)}")
        return v

    @field_validator("face_styles")
    @classmethod
    def val_face_styles(cls, v):
        if v is None:
            return v
        if len(v) > 6:
            raise ValueError(f"face_styles must have at most 6 entries, got {len(v)}")
        for s in v:
            if s is not None:
                _check_style(s, "face style")
        return v


class GenerateRequest(BaseModel):
    name: str = "My Building"
    faces: Optional[list[FaceData]] = None    # raw face list (advanced use)
    widgets: Optional[list[WidgetData]] = None
    rooms: Optional[list[RoomData]] = None    # cuboid editor format (preferred)

    @field_validator("name")
    @classmethod
    def val_name(cls, v):
        if len(v) > 256:
            raise ValueError("name must be 256 characters or fewer")
        return v

    @model_validator(mode="after")
    def val_not_empty(self):
        if not self.rooms and not self.faces:
            raise ValueError("provide either rooms or faces")
        if self.rooms and len(self.rooms) > _MAX_ROOMS:
            raise ValueError(f"too many rooms (max {_MAX_ROOMS})")
        if self.faces and len(self.faces) > _MAX_FACES:
            raise ValueError(f"too many faces (max {_MAX_FACES})")
        return self


# ---------------------------------------------------------------------------
# IFC generation (module-level so ProcessPoolExecutor can pickle it)
# ---------------------------------------------------------------------------

def _generate_ifc(request_dict: dict, share_dir: str) -> bytes:
    """CPU-bound work: build IFC from geometry data. Runs in a subprocess."""
    import sys, pathlib, os, tempfile
    _here = pathlib.Path(__file__).parent
    _root = _here.parent
    for p in (str(_here), str(_root)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from molior import Molior
    import molior.ifc as molior_ifc
    from geometry_adapter import faces_from_json, widgets_from_json, rooms_to_faces_and_widgets

    if request_dict.get("rooms"):
        faces, widgets = rooms_to_faces_and_widgets(request_dict["rooms"])
    else:
        faces = faces_from_json(request_dict.get("faces") or [])
        widgets = widgets_from_json(request_dict.get("widgets") or [])

    if not faces:
        raise ValueError("No geometry provided")

    ifc_file = molior_ifc.init(name=request_dict.get("name", "My Building"))
    molior_obj = Molior.from_faces_and_widgets(
        file=ifc_file,
        faces=faces,
        widgets=widgets,
        name=request_dict.get("name", "My Building"),
        share_dir=share_dir,
    )
    molior_obj.execute()

    # ifcopenshell.file.write() requires a file path, not a file-like object.
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".ifc")
    os.close(tmp_fd)
    try:
        ifc_file.write(tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def _validate_geometry(request_dict: dict, share_dir: str) -> dict:
    """Quick geometry check: build CellComplex only, no IFC generation."""
    import sys, pathlib
    _here = pathlib.Path(__file__).parent
    _root = _here.parent
    for p in (str(_here), str(_root)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from topologic_core import CellComplex
    from geometry_adapter import faces_from_json, widgets_from_json, rooms_to_faces_and_widgets

    if request_dict.get("rooms"):
        faces, _ = rooms_to_faces_and_widgets(request_dict["rooms"])
    else:
        faces = faces_from_json(request_dict.get("faces") or [])

    if not faces:
        return {"valid": False, "error": "No geometry provided"}

    cc = CellComplex.ByFaces(faces, 0.0001)
    cells, cc_faces = [], []
    cc.Cells(cc, cells)
    cc.Faces(cc, cc_faces)
    return {"valid": True, "cells": len(cells), "faces": len(cc_faces)}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Generate an IFC building from cuboid rooms or raw face geometry."""
    loop = asyncio.get_running_loop()
    try:
        ifc_bytes = await loop.run_in_executor(
            _executor,
            _generate_ifc,
            request.model_dump(),
            _share_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"IFC generation failed: {exc}")

    return Response(
        content=ifc_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="building.ifc"'},
    )


@app.get("/api/styles")
def list_styles():
    """List stylenames available in the share directory.

    "default" is always first — it is the root-level style (share/ itself,
    not a named subdirectory).  All other names are leaf subdirectory names
    that can be assigned to individual room faces.
    """
    share = pathlib.Path(_share_dir)
    if not share.is_dir():
        return {"styles": ["default"]}
    subdirs = sorted(
        d.name for d in share.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    return {"styles": ["default"] + subdirs}


@app.post("/api/validate")
async def validate(request: GenerateRequest):
    """Quick geometry validation: build CellComplex only (no full IFC generation)."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            _executor, _validate_geometry, request.model_dump(), _share_dir
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


@app.get("/health")
def health():
    return {"status": "ok", "share_dir": _share_dir}


# Serve the frontend — must come after API routes.
_static = _here / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
