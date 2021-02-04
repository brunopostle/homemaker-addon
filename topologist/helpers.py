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

def convert_to_stl_list(py_list, cppyy_data_type):
    values = create_stl_list(cppyy_data_type)
    for i in py_list:
        values.push_back(i)
    return values

def vertex_index(v, vertices):
    index = None
    i = 0
    for vertex in vertices:
        if v.IsSame(vertex):
            index = i
            break
        i += 1
    return index

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

def nx_acycles(digraph):
    """return all the acyclic chains in this digraph"""
    acycles = []
    for node in digraph.nodes():
        if len(list(digraph.predecessors(node))) == 0:
            acycle = [node]
            nx_successors(digraph, node, acycle)
            acycles.append(acycle)
    return acycles

def nx_successors(digraph, node, results):
    successors = digraph.successors(node)
    for successor in successors:
        results.append(successor)
        nx_successors(digraph, successor, results)
