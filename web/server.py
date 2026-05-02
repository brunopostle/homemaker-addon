"""homemaker-web FastAPI server.

Wraps the homemaker-addon Python library to expose IFC generation over HTTP.
The heavy lifting (topologic_core, ifcopenshell) runs server-side; the
browser receives a binary IFC file and renders it with @thatopen/components.
"""

import io
import os
import sys
import pathlib
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Locate the homemaker-addon package. When installed via pip the package is on
# sys.path already. When running from a clone, add the repo root.
_here = pathlib.Path(__file__).parent
_repo_root = _here.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from molior import Molior
import molior.ifc as molior_ifc
from geometry_adapter import faces_from_json, widgets_from_json, rooms_to_faces_and_widgets

# Locate share/ — works both from a git clone and from a pip-installed package.
try:
    import importlib.resources
    _share_dir = str(importlib.resources.files("molior").parent.parent / "share")
    if not pathlib.Path(_share_dir).is_dir():
        raise FileNotFoundError
except Exception:
    _share_dir = str(_repo_root / "share")

app = FastAPI(title="homemaker-web", version="0.1.0")

# One worker process for CPU-bound topologic_core work.
_executor = ProcessPoolExecutor(max_workers=2)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class FaceData(BaseModel):
    vertices: list[list[float]]
    stylename: str = "default"

class WidgetData(BaseModel):
    position: list[float]
    usage: str = "living"

class RoomData(BaseModel):
    position: list[float]          # [px, py, pz] min-corner
    size: list[float]              # [w, d, h]
    stylename: str = "default"
    usage: str = "living"

class GenerateRequest(BaseModel):
    name: str = "My Building"
    share_dir: Optional[str] = None  # style name or absolute path; None = server default
    faces: Optional[list[FaceData]] = None    # raw face list (advanced)
    widgets: Optional[list[WidgetData]] = None
    rooms: Optional[list[RoomData]] = None    # cuboid editor format (preferred)


# ---------------------------------------------------------------------------
# IFC generation (runs in executor to avoid blocking the event loop)
# ---------------------------------------------------------------------------

def _generate_ifc(request_dict: dict, share_dir: str) -> bytes:
    """CPU-bound work: build IFC from geometry data. Runs in a subprocess."""
    import sys, pathlib
    repo_root = pathlib.Path(__file__).parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from molior import Molior
    import molior.ifc as molior_ifc
    from geometry_adapter import faces_from_json, widgets_from_json, rooms_to_faces_and_widgets

    # Resolve share_dir: if the caller passed a bare style name (e.g. "simple"),
    # look it up under the server's share root.
    requested = request_dict.get("share_dir")
    if requested:
        candidate = pathlib.Path(share_dir) / requested
        if candidate.is_dir():
            resolved_share = str(candidate.parent)
        else:
            resolved_share = share_dir
    else:
        resolved_share = share_dir

    # Build face + widget lists
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
        share_dir=resolved_share,
    )
    molior_obj.execute()

    buf = io.StringIO()
    ifc_file.write(buf)
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Generate an IFC building from cuboid rooms or raw face geometry.

    Returns the IFC file as application/octet-stream.
    """
    import asyncio
    loop = asyncio.get_event_loop()
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
    """List available style names from the share directory."""
    share = pathlib.Path(_share_dir)
    if not share.is_dir():
        return {"styles": []}
    styles = sorted(
        d.name for d in share.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    return {"styles": styles, "share_dir": str(share)}


@app.post("/api/validate")
async def validate(request: GenerateRequest):
    """Quick geometry validation: build CellComplex only (no full IFC generation).

    Returns cell and face counts to give the client fast feedback.
    """
    import asyncio
    loop = asyncio.get_event_loop()

    def _validate(request_dict, share_dir):
        import sys, pathlib
        repo_root = pathlib.Path(__file__).parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
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

    try:
        result = await loop.run_in_executor(_executor, _validate, request.model_dump(), _share_dir)
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
