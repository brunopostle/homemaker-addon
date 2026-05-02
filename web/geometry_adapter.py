"""Convert JSON geometry data to topologic_core objects.

Replaces the Blender-specific topologic_faces_from_blender_object() and
process_blender_objects() functions from __init__.py.
"""

from topologic_core import Vertex, Face


def faces_from_json(face_data: list) -> list:
    """Convert a list of JSON face dicts to topologic_core.Face objects.

    Each face dict must have:
        vertices: list of [x, y, z] coordinates (3+ points, coplanar)
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
        position: [x, y, z]
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
        position:  [px, py, pz]  min-corner in metres
        size:      [w, d, h]     width, depth, height
        stylename: string
        usage:     string

    Returns (faces, widgets) ready for Molior.from_faces_and_widgets().
    """
    faces = []
    widgets = []
    for room in rooms:
        px, py, pz = room["position"]
        w, d, h = room["size"]
        stylename = room.get("stylename", "default")
        usage = room.get("usage", "living")

        px, py, pz = _snap([px, py, pz])
        w, d, h = round(w, 3), round(d, 3), round(h, 3)
        qx, qy, qz = px + w, py + d, pz + h

        verts = {
            "lbf": Vertex.ByCoordinates(px, py, pz),  # left-back-floor
            "rbf": Vertex.ByCoordinates(qx, py, pz),  # right-back-floor
            "rff": Vertex.ByCoordinates(qx, qy, pz),  # right-front-floor
            "lff": Vertex.ByCoordinates(px, qy, pz),  # left-front-floor
            "lbc": Vertex.ByCoordinates(px, py, qz),  # left-back-ceiling
            "rbc": Vertex.ByCoordinates(qx, py, qz),  # right-back-ceiling
            "rfc": Vertex.ByCoordinates(qx, qy, qz),  # right-front-ceiling
            "lfc": Vertex.ByCoordinates(px, qy, qz),  # left-front-ceiling
        }

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

        cx, cy, cz = px + w / 2, py + d / 2, pz + h / 2
        widget = Vertex.ByCoordinates(cx, cy, cz)
        widget.Set("usage", usage)
        widgets.append(widget)

    return faces, widgets


def _snap(coords: list) -> list:
    """Round coordinates to 3 decimal places to ensure face adjacency within tolerance."""
    return [round(float(c), 3) for c in coords]
