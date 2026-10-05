#!/usr/bin/python3

"""rooms2ifc - convert a rooms document into an IFC building

A rooms document is the JSON file saved by the web editor (rooms.json), see
web/README.md: a "rooms" list where each room has "vertices", "elevation",
"height", "face_styles" and "usage"; and an optional "name". Rooms are prisms,
anything else (a pitched roof) can be added with a "faces" list where each
face has "vertices" (three or more [x, y, z]) and a "stylename"; and a
"widgets" list where each has a "position" and a "usage". Other keys are
ignored.

Usage:
    rooms2ifc.py myrooms.json mybuilding.ifc

"""
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from molior import Molior
from molior.rooms import document_to_faces_and_widgets


def rooms2ifc(rooms_path, ifc_path):
    """Read a rooms document and write an IFC file"""
    with open(rooms_path) as handle:
        document = json.load(handle)
    # a bare list of rooms is accepted too
    if isinstance(document, list):
        document = {"rooms": document}
    faces, widgets = document_to_faces_and_widgets(document)
    if not faces:
        sys.exit(f"{rooms_path}: no rooms found")

    molior_object = Molior.from_faces_and_widgets(
        faces=faces,
        widgets=widgets,
        name=document.get("name") or "rooms2ifc building",
    )
    molior_object.execute()
    molior_object.file.write(ifc_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rooms2ifc(sys.argv[1], sys.argv[2])
