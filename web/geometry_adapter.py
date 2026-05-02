"""Convert JSON geometry data to topologic_core objects.

Replaces the Blender-specific topologic_faces_from_blender_object() and
process_blender_objects() functions from __init__.py.

Coordinate conventions
----------------------
Three.js uses Y-up:  X = east, Y = up (elevation), Z = north-south (depth)
IFC / homemaker uses Z-up: X = east, Y = north-south (depth), Z = up (elevation)

room["position"] arrives in Three.js convention; we swap axes here so that
the building geometry is correct in the generated IFC file:
  IFC X  = position[0]   (Three.js X, unchanged)
  IFC Y  = position[2]   (Three.js Z, north-south depth)
  IFC Z  = position[1]   (Three.js Y, elevation)
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
    """Convert a list of room dicts (cuboid editor format) to faces and widgets.

    Each room dict must have:
        position:  [px, py, pz]  in Three.js Y-up coords (px=east, py=elevation, pz=depth)
        size:      [w, d, h]     width (east), depth (north-south), height
        stylename: string
        usage:     string

    Coordinate swap applied here:
        IFC X = position[0], IFC Y = position[2], IFC Z = position[1]

    Returns (faces, widgets) ready for Molior.from_faces_and_widgets().
    """
    faces = []
    widgets = []
    for room in rooms:
        pos = room["position"]
        # Swap Three.js Y-up → IFC Z-up
        px = round(float(pos[0]), 3)   # east:  Three.js X  = IFC X
        py = round(float(pos[2]), 3)   # depth: Three.js Z  = IFC Y
        pz = round(float(pos[1]), 3)   # elev:  Three.js Y  = IFC Z

        w, d, h = (round(float(v), 3) for v in room["size"])
        qx, qy, qz = px + w, py + d, pz + h

        stylename = room.get("stylename", "default")
        usage = room.get("usage", "living")

        # 8 corners in IFC (Z-up) space
        verts = {
            "lbf": Vertex.ByCoordinates(px, py, pz),   # left-back-floor
            "rbf": Vertex.ByCoordinates(qx, py, pz),   # right-back-floor
            "rff": Vertex.ByCoordinates(qx, qy, pz),   # right-front-floor
            "lff": Vertex.ByCoordinates(px, qy, pz),   # left-front-floor
            "lbc": Vertex.ByCoordinates(px, py, qz),   # left-back-ceiling
            "rbc": Vertex.ByCoordinates(qx, py, qz),   # right-back-ceiling
            "rfc": Vertex.ByCoordinates(qx, qy, qz),   # right-front-ceiling
            "lfc": Vertex.ByCoordinates(px, qy, qz),   # left-front-ceiling
        }

        # All 6 faces — including ceiling — so partial overlaps with adjacent
        # rooms are handled correctly by CellComplex.ByFaces().
        face_vertex_groups = [
            [verts["lbf"], verts["rbf"], verts["rbc"], verts["lbc"]],  # back wall  (y=py)
            [verts["rbf"], verts["rff"], verts["rfc"], verts["rbc"]],  # right wall (x=qx)
            [verts["rff"], verts["lff"], verts["lfc"], verts["rfc"]],  # front wall (y=qy)
            [verts["lff"], verts["lbf"], verts["lbc"], verts["lfc"]],  # left wall  (x=px)
            [verts["lbf"], verts["rbf"], verts["rff"], verts["lff"]],  # floor      (z=pz)
            [verts["lbc"], verts["rbc"], verts["rfc"], verts["lfc"]],  # ceiling    (z=qz)
        ]

        for vg in face_vertex_groups:
            face = Face.ByVertices(vg)
            face.Set("stylename", stylename)
            faces.append(face)

        # Widget centroid in IFC space
        widget = Vertex.ByCoordinates(px + w / 2, py + d / 2, pz + h / 2)
        widget.Set("usage", usage)
        widgets.append(widget)

    return faces, widgets


def _snap(coords: list) -> list:
    """Round coordinates to 3 decimal places to ensure face adjacency within tolerance."""
    return [round(float(c), 3) for c in coords]
