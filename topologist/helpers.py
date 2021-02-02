from topologic import Vertex, Edge, Wire, Face, Shell, Cell, CellComplex, Cluster, Topology

import cppyy

def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()

def convert_to_stl_list(py_list, cppyy_data_type):
    values = create_stl_list(cppyy_data_type)
    for i in py_list:
        values.push_back(i)
    return values

def convert_to_py_list(stl_list):
    py_list = []
    i = stl_list.begin()
    while i != stl_list.end():
        py_list.append(i.__deref__())
        _ = i.__preinc__()
    return py_list

def classByType(argument):
    switcher = {
        1: Vertex,
        2: Edge,
        4: Wire,
        8: Face,
        16: Shell,
        32: Cell,
        64: CellComplex,
        128: Cluster}
    return switcher.get(argument, Topology)

def fixTopologyClass(topology):
    topology.__class__ = classByType(topology.GetType())
    return topology

def getSubTopologies(topology, subTopologyClass):
    pointer = subTopologyClass.Ptr
    values = cppyy.gbl.std.list[pointer]()
    if subTopologyClass == Vertex:
        _ = topology.Vertices(values)
    elif subTopologyClass == Edge:
        _ = topology.Edges(values)
    elif subTopologyClass == Wire:
        _ = topology.Wires(values)
    elif subTopologyClass == Face:
        _ = topology.Faces(values)
    elif subTopologyClass == Shell:
        _ = topology.Shells(values)
    elif subTopologyClass == Cell:
        _ = topology.Cells(values)
    elif subTopologyClass == CellComplex:
        _ = topology.CellComplexes(values)

    py_list = []
    i = values.begin()
    while i != values.end():
        py_list.append(fixTopologyClass(Topology.DeepCopy(i.__deref__())))
        _ = i.__preinc__()
    return py_list

def vertex_index(v, vertices):
    index = None
    i = 0
    for vertex in vertices:
        if v.IsSame(vertex):
            index = i
            break
        i += 1
    return index
