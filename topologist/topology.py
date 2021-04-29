"""Overloads domain-specific methods onto topologic.Topology"""

import cppyy
from cppyy.gbl.std import string
import topologic
from topologic import Vertex, Edge, Face, Cell, StringAttribute
from topologist.helpers import create_stl_list, el


def FacesVertical(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsVertical():
            faces_result.push_back(face)


def FacesHorizontal(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_result.push_back(face)


def FacesExternal(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsExternal():
            faces_result.push_back(face)
    return faces_result


def Elevation(self):
    lowest = 9999999.9
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return el(lowest)


def Height(self):
    highest = -9999999.9
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return el(highest - self.Elevation())


def EdgesTop(self, edges_result):
    """A list of horizontal edges at the highest level of this face"""
    edges = create_stl_list(Edge)
    self.Edges(edges)
    level = el(self.Elevation() + self.Height())
    for edge in edges:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            edges_result.push_back(edge)


def EdgesBottom(self, edges_result):
    """A list of horizontal edges at the lowest level of this face"""
    edges = create_stl_list(Edge)
    self.Edges(edges)
    level = self.Elevation()
    for edge in edges:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            edges_result.push_back(edge)


def EdgesCrop(self, edges_result):
    """Which edges are not vertical or top/bottom?"""
    edges = create_stl_list(Edge)
    self.Edges(edges)
    bottom = self.Elevation()
    top = el(self.Elevation() + self.Height())
    for edge in edges:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == top and el(vertex_end.Z()) == top:
            continue
        elif el(vertex_start.Z()) == bottom and el(vertex_end.Z()) == bottom:
            continue
        elif edge.IsVertical():
            continue
        edges_result.push_back(edge)


def Set(self, key, value):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(string(key)):
        dictionary.Remove(string(key))
    dictionary.Add(string(str(key)), StringAttribute(str(value)))
    self.SetDictionary(dictionary)


def Get(self, key):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(string(key)):
        value = dictionary.ValueAtKey(str(key))
        return str(cppyy.bind_object(value.Value(), "std::string"))
    return None


def DumpDictionary(self):
    dictionary = self.GetDictionary()
    keys = dictionary.Keys()
    result = {}
    for key in keys:
        value = self.Get(str(key))
        result[str(key)] = value
    return result


def GraphVertex(self, graph):
    index = self.Get("index")
    if self.__class__ == Face:
        myclass = "Face"
    if self.__class__ == Cell:
        myclass = "Cell"
    if not index == None:
        vertices = create_stl_list(Vertex)
        graph.Vertices(vertices)
        for vertex in vertices:
            if vertex.Get("index") == index and vertex.Get("class") == myclass:
                return vertex


def VertexId(self, vertex):
    i = 0
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    for v in vertices:
        if v.IsSame(vertex):
            return i
        i += 1


setattr(topologic.Topology, "FacesVertical", FacesVertical)
setattr(topologic.Topology, "FacesHorizontal", FacesHorizontal)
setattr(topologic.Topology, "FacesExternal", FacesExternal)
setattr(topologic.Topology, "Elevation", Elevation)
setattr(topologic.Topology, "Height", Height)
setattr(topologic.Topology, "EdgesTop", EdgesTop)
setattr(topologic.Topology, "EdgesBottom", EdgesBottom)
setattr(topologic.Topology, "EdgesCrop", EdgesCrop)
setattr(topologic.Topology, "Set", Set)
setattr(topologic.Topology, "Get", Get)
setattr(topologic.Topology, "DumpDictionary", DumpDictionary)
setattr(topologic.Topology, "GraphVertex", GraphVertex)
setattr(topologic.Topology, "VertexId", VertexId)
