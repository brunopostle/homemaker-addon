import cppyy
import topologic
from topologic import Vertex, Edge, Face, Cell, FaceUtility

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
    vertices_ptr = cppyy.gbl.std.list[Vertex.Ptr]()
    vertices = self.Vertices2(vertices_ptr)
    for vertex in vertices:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return lowest

def Height(self):
    highest = -9999999.9
    vertices_ptr = cppyy.gbl.std.list[Vertex.Ptr]()
    vertices = self.Vertices2(vertices_ptr)
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

def Vertices2(self, elements_ptr):
    _ = self.Vertices(elements_ptr)
    elementList = []
    i  =  elements_ptr.begin()
    while (i != elements_ptr.end()):
        elementList.append(i.__deref__())
        _ = i.__preinc__()
    for element in elementList:
        element.__class__ = cppyy.gbl.TopologicCore.Vertex
    return elementList

def Cells2(self, elements_ptr):
    _ = self.Cells(elements_ptr)
    elementList = []
    i  =  elements_ptr.begin()
    while (i != elements_ptr.end()):
        elementList.append(i.__deref__())
        _ = i.__preinc__()
    for element in elementList:
        element.__class__ = cppyy.gbl.TopologicCore.Cell
    return elementList

setattr(topologic.Face, 'Elevation', Elevation)
setattr(topologic.Face, 'Height', Height)
setattr(topologic.Face, 'IsVertical', IsVertical)
setattr(topologic.Face, 'IsHorizontal', IsHorizontal)
setattr(topologic.Face, 'Normal', Normal)
setattr(topologic.Face, 'Vertices2', Vertices2)
setattr(topologic.Face, 'Cells2', Cells2)
