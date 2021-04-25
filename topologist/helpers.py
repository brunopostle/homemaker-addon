from topologic import (
    Cell,
    CellComplex,
    Cluster,
    Edge,
    Face,
    Shell,
    Vertex,
    Wire,
    Topology,
)

import cppyy
from math import sqrt


def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()


def classByType(argument):
    switcher = {
        1: Vertex,
        2: Edge,
        4: Wire,
        8: Face,
        16: Shell,
        32: Cell,
        64: CellComplex,
        128: Cluster,
    }
    return switcher.get(argument, Topology)


def fixTopologyClass(topology):
    topology.__class__ = classByType(topology.GetType())
    return topology


def el(elevation):
    if elevation >= 0.0:
        return int((elevation * 1000) + 0.5) / 1000
    return int((elevation * 1000) - 0.5) / 1000


def vertex_string(vertex):
    return str(vertex.X()) + "__" + str(vertex.Y()) + "__" + str(vertex.Z())


def string_to_coor(string):
    return [float(num) for num in string.split("__")]


def string_to_coor_2d(string):
    split = string.split("__")
    return [float(split[0]), float(split[1])]


def vertex_id(topology, vertex):
    i = 0
    vertices = create_stl_list(Vertex)
    topology.Vertices(vertices)
    for v in vertices:
        if v.IsSame(vertex):
            return i
        i += 1


def x_product_3d(A, B):
    x = A[1] * B[2] - B[1] * A[2]
    y = A[2] * B[0] - B[2] * A[0]
    z = A[0] * B[1] - B[0] * A[1]
    return normalise_3d([x, y, z])


def normalise_3d(A):
    magnitude = magnitude_3d(A)
    if magnitude == 0.0:
        return [1.0, 0.0, 0.0]
    return scale_3d(A, 1.0 / magnitude)


def magnitude_3d(A):
    return distance_3d([0.0, 0.0, 0.0], A)


def scale_3d(A, B):
    if A.__class__ == [].__class__:
        return [A[0] * B, A[1] * B, A[2] * B]
    else:
        return [B[0] * A, B[1] * A, B[2] * A]


def subtract_3d(A, B):
    return [B[2] - A[2], B[1] - A[1], B[0] - A[0]]

def distance_3d(A, B):
    return sqrt((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2 + (A[2] - B[2]) ** 2)
