"""Hulls are 3D shells that define non-wall building elements,
differentiated by style properties.  Typically these define roofs,
soffits etc.

"""

from topologic import Vertex, Wire
from topologist.helpers import create_stl_list
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

        wires = create_stl_list(Wire)
        face.Wires(wires)
        vertices = create_stl_list(Vertex)
        list(wires)[0].Vertices(vertices)
        cells = face.CellsOrdered()

        hulls[label][stylename].add_face(
            [vertex.Coordinates() for vertex in vertices], face.Normal(), [face, *cells]
        )

    def process(self):
        """add_face() leaves the hull as a single uhull, split into a list of uhull shells"""
        hulls = self.hulls
        for label in hulls:
            for stylename in hulls[label]:
                if not type(hulls[label][stylename]) == list:
                    hulls[label][stylename] = hulls[label][stylename].decompose()
