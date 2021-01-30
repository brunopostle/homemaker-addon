import topologic
from topologic import Face, CellComplex
from topologist.helpers import create_stl_list

def ByFaces2(faces, tolerance):
    faces_ptr = create_stl_list(Face)
    for face in faces:
        faces_ptr.push_back(face)
    return CellComplex.ByFaces(faces_ptr, tolerance)

setattr(topologic.CellComplex, 'ByFaces2', ByFaces2)
