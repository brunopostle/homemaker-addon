import cppyy
import topologic
from topologic import CellUtility
from .helpers import getSubTopologies

def Volume(self):
    return CellUtility.Volume(self)

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

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
