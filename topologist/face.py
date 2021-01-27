import cppyy
import topologic
from topologic import Vertex, Edge, Face, FaceUtility
from .helpers import *

def ByVertices(vertices):
    edges = []
    for i in range(len(vertices)-1):
        v1 = vertices[i]
        v2 = vertices[i+1]
        e1 = Edge.ByStartVertexEndVertex(v1, v2)
        edges.append(e1)
    # connect the last vertex to the first one
    v1 = vertices[len(vertices)-1]
    v2 = vertices[0]
    e1 = Edge.ByStartVertexEndVertex(v1, v2)
    edges.append(e1)
    return ByEdges2(edges)

def ByEdges2(edges):
    edges_ptr = cppyy.gbl.std.list[topologic.Edge.Ptr]()
    for edge in edges:
        edges_ptr.push_back(edge)
    return Face.ByEdges(edges_ptr)

setattr(topologic.Face, 'ByVertices', ByVertices)
setattr(topologic.Face, 'ByEdges2', ByEdges2)

def Elevation(self):
    lowest = 9999999.9
    vertices = getSubTopologies(self, Vertex)
    for vertex in vertices:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return lowest

def Height(self):
    highest = -9999999.9
    vertices = getSubTopologies(self, Vertex)
    for vertex in vertices:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return highest - self.Elevation()

def IsVertical(self):
    normal = self.Normal()
    if abs(normal.Z()) < 0.0001:
        return True
    return False

def IsHorizontal(self):
    normal = self.Normal()
    if abs(normal.Z()) > 0.9999:
        return True
    return False

def Normal(self):
    return FaceUtility.NormalAtParameters(self, 0.5, 0.5)

setattr(topologic.Face, 'Elevation', Elevation)
setattr(topologic.Face, 'Height', Height)
setattr(topologic.Face, 'IsVertical', IsVertical)
setattr(topologic.Face, 'IsHorizontal', IsHorizontal)
setattr(topologic.Face, 'Normal', Normal)