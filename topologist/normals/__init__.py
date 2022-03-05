"""Normals are unit vectors indicating the local vertex orientation.
Here they are used to tell walls and extrusions how to mitre properly.

"""

import numpy
from topologist.helpers import el


class Normals:
    def __init__(self):
        self.normals = {"bottom": {}, "top": {}}

    def add_vector(self, label, vertex, vector):
        """Add a 3D vector to the location defined by a Topologic Vertex"""
        if not label in self.normals:
            self.normals[label] = {}

        if vertex.__class__ == [].__class__:
            vertex_str = (
                str(vertex[0]) + "__" + str(vertex[1]) + "__" + str(el(vertex[2]))
            )
        else:
            vertex_str = (
                str(vertex.X()) + "__" + str(vertex.Y()) + "__" + str(el(vertex.Z()))
            )

        if vertex_str in self.normals[label]:
            self.normals[label][vertex_str] = numpy.add(
                self.normals[label][vertex_str], vector
            )
        else:
            self.normals[label][vertex_str] = vector

    def process(self):
        """add_vector() increments the magnitude, normalise to 1.0"""
        for label in self.normals:
            for vertex_str in self.normals[label]:
                self.normals[label][vertex_str] /= numpy.linalg.norm(
                    self.normals[label][vertex_str]
                )
