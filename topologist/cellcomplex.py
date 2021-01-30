import cppyy
import topologic
from topologic import Face, CellComplex

def ByFaces2(faces, tolerance):
    faces_ptr = cppyy.gbl.std.list[Face.Ptr]()
    for face in faces:
        faces_ptr.push_back(face)
    return CellComplex.ByFaces(faces_ptr, tolerance)

setattr(topologic.CellComplex, 'ByFaces2', ByFaces2)

