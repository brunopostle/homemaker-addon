"""Convert JSON geometry data to topologic_core objects.

Coordinate conventions
----------------------
Three.js uses Y-up:  X = east, Y = up (elevation), Z = north-south (depth)
IFC / homemaker uses Z-up: X = east, Y = north-south (depth), Z = up (elevation)

All rooms are sent as quad cells:
  room["vertices"]  — [[three_x, three_z], ...]  in Three.js XZ plane
  room["elevation"] — Three.js Y (floor height)
  room["height"]    — room height

IFC coordinates:
  IFC X  = three_x       (east, unchanged)
  IFC Y  = three_z       (depth, Three.js Z → IFC Y)
  IFC Z  = elevation     (Three.js Y elevation → IFC Z)

face_styles index: 0=floor, 1=ceiling, 2..n+1=walls in vertex order.
"""

import topologist  # applies Face.ByVertices / Vertex.Set monkey-patches
from topologic_core import Vertex, Face


def faces_from_json(face_data: list) -> list:
    """Convert a list of JSON face dicts to topologic_core.Face objects.

    Each face dict must have:
        vertices: list of [x, y, z] coordinates in IFC/Z-up space (3+ points, coplanar)
        stylename: string style name (optional, defaults to "default")
    """
    faces = []
    for item in face_data:
        raw_verts = item.get("vertices", [])
        if len(raw_verts) < 3:
            continue
        stylename = item.get("stylename", "default")
        vertices = [Vertex.ByCoordinates(*_snap(v)) for v in raw_verts]
        face = Face.ByVertices(vertices)
        face.Set("stylename", stylename)
        faces.append(face)
    return faces


def widgets_from_json(widget_data: list) -> list:
    """Convert a list of JSON widget dicts to topologic_core.Vertex objects.

    Each widget dict must have:
        position: [x, y, z] in IFC/Z-up space
        usage:    string room type (bedroom, kitchen, living, etc.)
    """
    widgets = []
    for item in widget_data:
        pos = item.get("position", [])
        if len(pos) < 3:
            continue
        usage = item.get("usage", "living")
        vertex = Vertex.ByCoordinates(*_snap(pos))
        vertex.Set("usage", usage)
        widgets.append(vertex)
    return widgets


def rooms_to_faces_and_widgets(rooms: list) -> tuple:
    """Convert a list of room dicts (editor format) to faces and widgets.

    Every room must have "vertices" (list of [three_x, three_z] pairs),
    "elevation", and "height".  Returns (faces, widgets) ready for
    Molior.from_faces_and_widgets().
    """
    faces, widgets = [], []
    for room in rooms:
        f, w = _room(room)
        faces.extend(f)
        widgets.append(w)
    return faces, widgets


def _room(room: dict) -> tuple:
    """Convert a quad-cell room dict to (faces, widget).

    room["vertices"] is [[three_x, three_z], ...] in Three.js XZ coords.
    face_styles index: 0=floor, 1=ceiling, 2..n+1=walls in vertex order.
    """
    vertices_2d = room["vertices"]  # [[three_x, three_z], ...]
    elevation = round(float(room.get("elevation", 0)), 3)
    height    = round(float(room.get("height", 3)), 3)
    n = len(vertices_2d)
    stylename = room.get("stylename", "default")

    ifc_floor_z = elevation
    ifc_ceil_z  = elevation + height

    # IFC X = three_x, IFC Y = three_z (depth), IFC Z = elevation
    floor_verts = [
        Vertex.ByCoordinates(round(float(v[0]), 3), round(float(v[1]), 3), ifc_floor_z)
        for v in vertices_2d
    ]
    ceil_verts = [
        Vertex.ByCoordinates(round(float(v[0]), 3), round(float(v[1]), 3), ifc_ceil_z)
        for v in vertices_2d
    ]

    raw_face_styles = room.get("face_styles") or []

    def fstyle(i):
        if i < len(raw_face_styles) and raw_face_styles[i]:
            return raw_face_styles[i]
        return stylename

    faces = []
    floor_face = Face.ByVertices(floor_verts)
    floor_face.Set("stylename", fstyle(0))
    faces.append(floor_face)

    ceil_face = Face.ByVertices(ceil_verts)
    ceil_face.Set("stylename", fstyle(1))
    faces.append(ceil_face)

    for i in range(n):
        j = (i + 1) % n
        wall = Face.ByVertices([floor_verts[i], floor_verts[j], ceil_verts[j], ceil_verts[i]])
        wall.Set("stylename", fstyle(2 + i))
        faces.append(wall)

    cx = round(sum(float(v[0]) for v in vertices_2d) / n, 3)
    cy = round(sum(float(v[1]) for v in vertices_2d) / n, 3)
    cz = round(elevation + height / 2, 3)
    widget = Vertex.ByCoordinates(cx, cy, cz)
    widget.Set("usage", room.get("usage", "living"))
    return faces, widget


def _snap(coords: list) -> list:
    """Round coordinates to 3 decimal places to ensure face adjacency within tolerance."""
    return [round(float(c), 3) for c in coords]
