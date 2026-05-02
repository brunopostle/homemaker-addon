"""Convert JSON geometry data to topologic_core objects.

Replaces the Blender-specific topologic_faces_from_blender_object() and
process_blender_objects() functions from __init__.py.

Coordinate conventions
----------------------
Three.js uses Y-up:  X = east, Y = up (elevation), Z = north-south (depth)
IFC / homemaker uses Z-up: X = east, Y = north-south (depth), Z = up (elevation)

Cuboid rooms
  room["position"] arrives in Three.js convention; we swap axes:
    IFC X  = position[0]   (Three.js X, unchanged)
    IFC Y  = position[2]   (Three.js Z, north-south depth)
    IFC Z  = position[1]   (Three.js Y, elevation)

Polygon rooms
  room["vertices"] is [[three_x, three_z], ...] in Three.js XZ plane.
  IFC coordinates:
    IFC X  = three_x       (east, unchanged)
    IFC Y  = three_z       (depth, Three.js Z → IFC Y)
    IFC Z  = elevation     (Three.js Y elevation → IFC Z)
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

    Dispatches to _cuboid_room or _polygon_room based on whether "vertices"
    is present.  Returns (faces, widgets) ready for Molior.from_faces_and_widgets().
    """
    faces, widgets = [], []
    for room in rooms:
        if room.get("vertices"):
            f, w = _polygon_room(room)
        else:
            f, w = _cuboid_room(room)
        faces.extend(f)
        widgets.append(w)
    return faces, widgets


def _cuboid_room(room: dict) -> tuple:
    """Convert a cuboid room dict to (faces, widget)."""
    pos = room["position"]
    # Swap Three.js Y-up → IFC Z-up
    px = round(float(pos[0]), 3)   # east:  Three.js X  = IFC X
    py = round(float(pos[2]), 3)   # depth: Three.js Z  = IFC Y
    pz = round(float(pos[1]), 3)   # elev:  Three.js Y  = IFC Z

    w, d, h = (round(float(v), 3) for v in room["size"])
    qx, qy, qz = px + w, py + d, pz + h

    stylename = room.get("stylename", "default")
    usage = room.get("usage", "living")

    verts = {
        "lbf": Vertex.ByCoordinates(px, py, pz),
        "rbf": Vertex.ByCoordinates(qx, py, pz),
        "rff": Vertex.ByCoordinates(qx, qy, pz),
        "lff": Vertex.ByCoordinates(px, qy, pz),
        "lbc": Vertex.ByCoordinates(px, py, qz),
        "rbc": Vertex.ByCoordinates(qx, py, qz),
        "rfc": Vertex.ByCoordinates(qx, qy, qz),
        "lfc": Vertex.ByCoordinates(px, qy, qz),
    }

    raw_face_styles = room.get("face_styles") or []
    face_styles = [
        (raw_face_styles[i] if i < len(raw_face_styles) and raw_face_styles[i]
         else stylename)
        for i in range(6)
    ]

    face_vertex_groups = [
        [verts["lbf"], verts["rbf"], verts["rff"], verts["lff"]],  # 0: floor
        [verts["rbf"], verts["rff"], verts["rfc"], verts["rbc"]],  # 1: right wall
        [verts["lbc"], verts["rbc"], verts["rfc"], verts["lfc"]],  # 2: ceiling
        [verts["lff"], verts["lbf"], verts["lbc"], verts["lfc"]],  # 3: left wall
        [verts["lbf"], verts["rbf"], verts["rbc"], verts["lbc"]],  # 4: back wall
        [verts["rff"], verts["lff"], verts["lfc"], verts["rfc"]],  # 5: front wall
    ]

    faces = []
    for i, vg in enumerate(face_vertex_groups):
        face = Face.ByVertices(vg)
        face.Set("stylename", face_styles[i])
        faces.append(face)

    widget = Vertex.ByCoordinates(px + w / 2, py + d / 2, pz + h / 2)
    widget.Set("usage", usage)
    return faces, widget


def _polygon_room(room: dict) -> tuple:
    """Convert a polygon room dict to (faces, widget).

    room["vertices"] is [[three_x, three_z], ...] in Three.js XZ coords.
    face_styles index: 0=floor, 1=ceiling, 2..n+1=walls in vertex order.
    """
    vertices_2d = room["vertices"]  # [[three_x, three_z], ...]
    elevation = round(float(room.get("elevation", 0)), 3)
    height    = round(float(room.get("height", 3)), 3)
    n = len(vertices_2d)
    stylename = room.get("stylename", "default")

    # IFC Z = elevation (floor) or elevation+height (ceiling)
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

    # Widget centroid in IFC space
    cx = round(sum(float(v[0]) for v in vertices_2d) / n, 3)
    cy = round(sum(float(v[1]) for v in vertices_2d) / n, 3)
    cz = round(elevation + height / 2, 3)
    widget = Vertex.ByCoordinates(cx, cy, cz)
    widget.Set("usage", room.get("usage", "living"))
    return faces, widget


def _snap(coords: list) -> list:
    """Round coordinates to 3 decimal places to ensure face adjacency within tolerance."""
    return [round(float(c), 3) for c in coords]
