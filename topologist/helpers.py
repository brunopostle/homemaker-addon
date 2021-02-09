from topologic import Vertex, Edge, Wire, Face, Shell, Cell, CellComplex, Cluster, Topology

import cppyy

def dummy():
    """dummy method to trick linter"""
    Vertex()
    Vertex()
    Edge()
    Wire()
    Face()
    Shell()
    Cell()
    CellComplex()
    Cluster()
    Topology()

def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()

def el(elevation):
    if elevation >= 0.0:
        return int((elevation * 1000) +0.5) /1000
    return int((elevation * 1000) -0.5) /1000

def vertex_string(vertex):
    return str(vertex.X()) + '__' + str(vertex.Y()) + '__' + str(vertex.Z())

def string_to_coor(string):
    coor = []
    for num in string.split('__'):
        coor.append(float(num))
    return coor
