import topologic
from topologic import CellUtility
from .helpers import *

def Volume(self):
    return CellUtility.Volume(self)

def FacesTop(self):
    faces = getSubTopologies(self, Face)
    faces_result = []
    for face in faces:
        if(face.Elevation() == self.Elevation() + self.Height() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

def FacesBottom(self):
    faces = getSubTopologies(self, Face)
    faces_result = []
    for face in faces:
        if(face.Elevation() == self.Elevation() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

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

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
setattr(topologic.Cell, 'Elevation', Elevation)
setattr(topologic.Cell, 'Height', Height)
