"""Normals are unit vectors indicating the local vertex orientation.
Here they are used to tell walls and extrusions how to mitre properly.

"""

from molior.geometry import normalise_3d, add_3d


class Normals:
    def __init__(self):
        self.normals = {"bottom": {}, "top": {}}

    def add_vector(self, label, vertex, vector):
        """Add a 3D vector to the location defined by a Topologic Vertex"""
        if not label in self.normals:
            self.normals[label] = {}

        vertex_str = vertex.String()

        if vertex_str in self.normals[label]:
            self.normals[label][vertex_str] = add_3d(
                self.normals[label][vertex_str], vector
            )
        else:
            self.normals[label][vertex_str] = vector

    def process(self):
        """add_vector() increments the magnitude, normalise to 1.0"""
        for label in self.normals:
            for vertex_str in self.normals[label]:
                self.normals[label][vertex_str] = normalise_3d(
                    self.normals[label][vertex_str]
                )
