import cppyy
import topologic
from topologic import Face, CellComplex

def ByFaces2(faces, tolerance):
    faces_ptr = cppyy.gbl.std.list[Face.Ptr]()
    for face in faces:
        faces_ptr.push_back(face)
    return CellComplex.ByFaces(faces_ptr, tolerance)

setattr(topologic.CellComplex, 'ByFaces2', ByFaces2)

def FacesVertical(self, faces_ptr):
    faces = self.Faces2(faces_ptr)
    faces_result = []
    for face in faces:
        if face.IsVertical():
            faces_result.append(face)
    return faces_result

def FacesHorizontal(self, faces_ptr):
    faces = self.Faces2(faces_ptr)
    faces_result = []
    for face in faces:
        if face.IsHorizontal():
            faces_result.append(face)
    return faces_result

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

setattr(topologic.CellComplex, 'FacesVertical', FacesVertical)
setattr(topologic.CellComplex, 'FacesHorizontal', FacesHorizontal)
setattr(topologic.CellComplex, 'Faces2', Faces2)
setattr(topologic.CellComplex, 'Cells2', Cells2)
