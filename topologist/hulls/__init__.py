"""Hulls are 3D shells that define planar building elements, differentiated by
style properties.  Typically these define roofs, soffits etc.. and are drawn
using a simple thickened plate corresponding to the original Face.

There are hulls for these conditions:

* external-panel (a vertical wall that doesn't have a horizontal bottom edge)
* internal-panel (a vertical wall that doesn't have a horizontal bottom edge)
* flat (a flat roof)
* roof (an inclined roof)
* soffit (a non-vertical soffit)
* vault (a non-vertical divider between internal spaces)

In addition, there are hulls that correspond to identically named traces.

Each wall condition with horizontal bottom edges:

* external (a vertical wall between inside and outside)
* internal (a vertical wall between twon internal spaces)
* open (an external 'wall' to outside space)

Each cell floor perimeter, note that internal shell faces have no up or down
orientation, use the equivalent trace instead:

* kitchen
* living
* bedroom
* toilet
* sahn (an outside circulation space)
* circulation
* stair
* retail
* outside
* void (an internal space that doesn't qualify as a room)

"""

import topologist.ushell as ushell


class Hulls:
    def __init__(self):
        self.hulls = {}

    def add_face(self, label, stylename, face=None, front_cell=None, back_cell=None):
        """Add a Topologic Face object, will split to contiguous shells later"""
        hulls = self.hulls
        if not label in hulls:
            hulls[label] = {}
        if not stylename in hulls[label]:
            hulls[label][stylename] = ushell.shell()

        vertices_ptr = []
        face.VerticesPerimeter(vertices_ptr)

        hulls[label][stylename].add_facet(
            [vertex.Coordinates() for vertex in vertices_ptr],
            {"face": face, "back_cell": back_cell, "front_cell": front_cell},
        )

    def process(self):
        """add_face() leaves the hull as a single uhull, split into a list of uhull shells"""
        hulls = self.hulls
        for label in hulls:
            for stylename in hulls[label]:
                if not type(hulls[label][stylename]) == list:
                    hulls[label][stylename] = hulls[label][stylename].decompose()
