import cppyy
import topologic
from topologic import Cell, CellUtility
from .helpers import *

def Volume(self):
    return CellUtility.Volume(self)

def Elevation(self):
    lowest = 9999999.9
    vertices = getSubTopologies(self, Vertex)
    for vertex in vertices:
        if(vertex.Z() < lowest):
            lowest = vertex.Z()
    return lowest

def Height(self):
    highest = -9999999.9
    vertices = getSubTopologies(self, Vertex)
    for vertex in vertices:
        if(vertex.Z() > highest):
            highest = vertex.Z()
    return highest - self.Elevation()

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'Elevation', Elevation)
setattr(topologic.Cell, 'Height', Height)
