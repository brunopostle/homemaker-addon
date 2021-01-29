import cppyy
import topologic
from topologic import Vertex

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

def Faces2(self, elements_ptr):
    _ = self.Faces(elements_ptr)
    elementList = []
    i  =  elements_ptr.begin()
    while (i != elements_ptr.end()):
        elementList.append(i.__deref__())
        _ = i.__preinc__()
    for element in elementList:
        element.__class__ = cppyy.gbl.TopologicCore.Face
    return elementList

def FacesVertical(self, elements_ptr):
    faces = self.Faces2(elements_ptr)
    faces_result = []
    for face in faces:
        if face.IsVertical():
            faces_result.append(face)
    return faces_result

def FacesHorizontal(self, elements_ptr):
    faces = self.Faces2(elements_ptr)
    faces_result = []
    for face in faces:
        if face.IsHorizontal():
            faces_result.append(face)
    return faces_result

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

setattr(topologic.Topology, 'Vertices2', Vertices2)
setattr(topologic.Topology, 'Faces2', Faces2)
setattr(topologic.Topology, 'FacesVertical', FacesVertical)
setattr(topologic.Topology, 'FacesHorizontal', FacesHorizontal)
setattr(topologic.Topology, 'Cells2', Cells2)
setattr(topologic.Topology, 'Elevation', Elevation)
setattr(topologic.Topology, 'Height', Height)

