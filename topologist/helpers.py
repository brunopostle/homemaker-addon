from topologic import Aperture, Cell, CellComplex, Cluster, Edge, Face, Shell, Vertex, Wire, Topology

import cppyy

def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()

def init_stl_lists():
    """workaround cppyy problem"""
    cppyy.gbl.TopologicCore.Aperture.Ptr = cppyy.gbl.TopologicCore.Aperture.__class__.Ptr
    cppyy.gbl.TopologicCore.Cell.Ptr = cppyy.gbl.TopologicCore.Cell.__class__.Ptr
    cppyy.gbl.TopologicCore.CellComplex.Ptr = cppyy.gbl.TopologicCore.CellComplex.__class__.Ptr
    cppyy.gbl.TopologicCore.Cluster.Ptr = cppyy.gbl.TopologicCore.Cluster.__class__.Ptr
    cppyy.gbl.TopologicCore.Edge.Ptr = cppyy.gbl.TopologicCore.Edge.__class__.Ptr
    cppyy.gbl.TopologicCore.Face.Ptr = cppyy.gbl.TopologicCore.Face.__class__.Ptr
    cppyy.gbl.TopologicCore.Shell.Ptr = cppyy.gbl.TopologicCore.Shell.__class__.Ptr
    cppyy.gbl.TopologicCore.Vertex.Ptr = cppyy.gbl.TopologicCore.Vertex.__class__.Ptr
    cppyy.gbl.TopologicCore.Wire.Ptr = cppyy.gbl.TopologicCore.Wire.__class__.Ptr

def classByType(argument):
    switcher = {
      1: Vertex,
      2: Edge,
      4: Wire,
      8: Face,
      16: Shell,
      32: Cell,
      64: CellComplex,
      128: Cluster }
    return switcher.get(argument, Topology)

def fixTopologyClass(topology):
    topology.__class__ = classByType(topology.GetType())
    return topology

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
