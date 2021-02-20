from topologic import Vertex, Edge, Wire, Face, Shell, Cell, CellComplex, Cluster, Topology

import cppyy

def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()

def init_stl_lists():
    """workaround cppyy problem"""
    create_stl_list(Aperture)
    create_stl_list(Cell)
    create_stl_list(CellComplex)
    create_stl_list(Cluster)
    create_stl_list(Edge)
    create_stl_list(Face)
    create_stl_list(Shell)
    create_stl_list(Vertex)
    create_stl_list(Wire)
    # do this last otherwise everything ends up as Topology
    create_stl_list(Topology)

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

def string_to_coor_2d(string):
    coor = []
    split = string.split('__')
    coor.extend([float(split[0]), float(split[1])])
    return coor

def vertex_id(topology, vertex):
    i = 0
    vertices = create_stl_list(Vertex)
    topology.Vertices(vertices)
    for v in vertices:
        if v.IsSame(vertex):
            return i
        i += 1
    return None
