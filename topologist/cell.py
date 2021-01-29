import cppyy
import topologic
from topologic import Vertex, Face, CellUtility
from .helpers import getSubTopologies

def Volume(self):
    return CellUtility.Volume(self)

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

def FacesTop(self, elements_ptr):
    faces = self.Faces2(elements_ptr)
    faces_result = []
    for face in faces:
        if(face.Elevation() == self.Elevation() + self.Height() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

def FacesBottom(self, elements_ptr):
    faces = self.Faces2(elements_ptr)
    faces_result = []
    for face in faces:
        if(face.Elevation() == self.Elevation() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

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

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'Vertices2', Vertices2)
setattr(topologic.Cell, 'Faces2', Faces2)
setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
setattr(topologic.Cell, 'Elevation', Elevation)
setattr(topologic.Cell, 'Height', Height)
