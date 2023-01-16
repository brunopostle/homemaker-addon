"""Overloads domain-specific methods onto topologic.Topology"""

from functools import lru_cache
import topologic
from topologic import StringAttribute, Vertex, FaceUtility
from topologist.helpers import el


@lru_cache(maxsize=256)
def Cells_Cached(self, host_topology):
    """List of Cells directly attached to this Topology"""
    cells_ptr = []
    self.Cells(host_topology, cells_ptr)
    return cells_ptr


@lru_cache(maxsize=256)
def Faces_Cached(self, host_topology):
    """List of Faces directly attached to this Topology"""
    faces_ptr = []
    self.Faces(host_topology, faces_ptr)
    return faces_ptr


def FacesVertical(self, faces_ptr):
    """List of vertical Faces within this Topology"""
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if face.IsVertical():
            faces_ptr.append(face)


# FIXME doesn't appear to be in use
def FacesHorizontal(self, faces_ptr):
    """List of horizontal Faces within this Topology"""
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_ptr.append(face)


def FacesInclined(self, faces_ptr):
    """List of inclined Faces within this Topology"""
    if self.__class__ == Vertex:
        # Faces() is for searching sub-topologies and a Vertex has none
        return
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if not face.IsHorizontal() and not face.IsVertical():
            faces_ptr.append(face)


def FacesWorld(self, host_topology):
    """List of external world Faces directly attached to this Topology"""
    faces_ptr = []
    elements_ptr = self.Faces_Cached(host_topology)
    for face in elements_ptr:
        if face.IsWorld(host_topology):
            faces_ptr.append(face)
    return faces_ptr


@lru_cache(maxsize=256)
def Elevation(self):
    """Lowest Z-height in this Topology"""
    lowest = 9999999.9
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for vertex in vertices_ptr:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return el(lowest)


@lru_cache(maxsize=256)
def Height(self):
    """Vertical distance between the lowest and highest points in this Topology"""
    highest = -9999999.9
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for vertex in vertices_ptr:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return el(highest - self.Elevation())


def Mesh(self):
    """Returns a list of Vertex coordinates, and a list of indexed Faces"""
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    vertices = [vertex.Coordinates() for vertex in vertices_ptr]

    faces_ptr = []
    self.Faces(None, faces_ptr)
    faces = []
    for face in faces_ptr:
        wire_vertices_ptr = []
        face.ExternalBoundary().Vertices(None, wire_vertices_ptr)
        faces.append([self.VertexId(vertex) for vertex in wire_vertices_ptr])
    return vertices, faces


def Set(self, key, value):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(str(key)):
        dictionary.Remove(str(key))
    dictionary.Add(str(str(key)), StringAttribute(str(value)))
    self.SetDictionary(dictionary)


def Get(self, key):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(str(key)):
        value = dictionary.ValueAtKey(str(key))
        return str(value.StringValue())
    return None


def DumpDictionary(self):
    """Dump string attributes as a python dictionary"""
    dictionary = self.GetDictionary()
    keys = dictionary.Keys()
    result = {}
    for key in keys:
        value = self.Get(str(key))
        result[str(key)] = value
    return result


def GraphVertex(self, graph):
    """What Vertex in a given Graph corresponds with this Topology"""
    index = self.Get("index")
    myclass = type(self).__name__
    if not index == None:
        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        for vertex in vertices_ptr:
            if vertex.Get("index") == index and vertex.Get("class") == myclass:
                return vertex


@lru_cache(maxsize=256)
def VertexId(self, vertex):
    i = 0
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for v in vertices_ptr:
        if v.IsSame(vertex):
            return i
        i += 1


def ApplyDictionary(self, source_faces_ptr):
    """Copy Dictionary items from a list of Faces onto this CellComplex"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        vertex = FaceUtility.InternalVertex(face, 0.001)
        for source_face in source_faces_ptr:
            if FaceUtility.IsInside(source_face, vertex, 0.001):
                dictionary = source_face.GetDictionary()
                for key in dictionary.Keys():
                    face.Set(key, source_face.Get(key).split(".")[0])
                break


setattr(topologic.Topology, "Cells_Cached", Cells_Cached)
setattr(topologic.Topology, "Faces_Cached", Faces_Cached)
setattr(topologic.Topology, "FacesVertical", FacesVertical)
setattr(topologic.Topology, "FacesHorizontal", FacesHorizontal)
setattr(topologic.Topology, "FacesInclined", FacesInclined)
setattr(topologic.Topology, "FacesWorld", FacesWorld)
setattr(topologic.Topology, "Elevation", Elevation)
setattr(topologic.Topology, "Height", Height)
setattr(topologic.Topology, "Mesh", Mesh)
setattr(topologic.Topology, "Set", Set)
setattr(topologic.Topology, "Get", Get)
setattr(topologic.Topology, "DumpDictionary", DumpDictionary)
setattr(topologic.Topology, "GraphVertex", GraphVertex)
setattr(topologic.Topology, "VertexId", VertexId)
setattr(topologic.Topology, "ApplyDictionary", ApplyDictionary)
