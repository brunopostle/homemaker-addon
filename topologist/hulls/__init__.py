import topologist.ushell as ushell


class Hulls:
    """Hulls are 3D shells that define planar building elements"""

    def __init__(self):
        self.hulls = {}

    def add_face(self, label, stylename, face=None, front_cell=None, back_cell=None):
        """Add a Topologic Face object, will split to contiguous shells later"""
        hulls = self.hulls
        if label not in hulls:
            hulls[label] = {}
        if stylename not in hulls[label]:
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
