"""Hulls are 3D shells that define non-wall building elements,
differentiated by style properties.  Typically these define roofs,
soffits etc.

"""

import topologist.ushell as ushell


class Hulls:
    def __init__(self):
        self.hulls = {}

    def add_face(self, label, stylename, face):
        """Add a Topologic Face object, will split to contiguous shells later"""
        hulls = self.hulls
        if not label in hulls:
            hulls[label] = {}
        if not stylename in hulls[label]:
            hulls[label][stylename] = ushell.shell()

        vertices_ptr = []
        face.VerticesPerimeter(vertices_ptr)
        cells = face.CellsOrdered()

        hulls[label][stylename].add_face(
            [vertex.Coordinates() for vertex in vertices_ptr],
            face.Normal(),
            [face, cells[1], cells[0]],
        )

    def process(self):
        """add_face() leaves the hull as a single uhull, split into a list of uhull shells"""
        hulls = self.hulls
        for label in hulls:
            for stylename in hulls[label]:
                if not type(hulls[label][stylename]) == list:
                    hulls[label][stylename] = hulls[label][stylename].decompose()
