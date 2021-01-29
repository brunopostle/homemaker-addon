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

setattr(topologic.CellComplex, 'FacesVertical', FacesVertical)
setattr(topologic.CellComplex, 'FacesHorizontal', FacesHorizontal)
