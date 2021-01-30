import cppyy
import topologic
from topologic import Vertex

def FacesVertical(self):
    elements_ptr = cppyy.gbl.std.list[topologic.Face.Ptr]()
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if face.IsVertical():
            faces_result.append(face)
    return faces_result

def FacesHorizontal(self):
    elements_ptr = cppyy.gbl.std.list[topologic.Face.Ptr]()
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_result.append(face)
    return faces_result

def Elevation(self):
    lowest = 9999999.9
    vertices = cppyy.gbl.std.list[Vertex.Ptr]()
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return lowest

def Height(self):
    highest = -9999999.9
    vertices = cppyy.gbl.std.list[Vertex.Ptr]()
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return highest - self.Elevation()

setattr(topologic.Topology, 'FacesVertical', FacesVertical)
setattr(topologic.Topology, 'FacesHorizontal', FacesHorizontal)
setattr(topologic.Topology, 'Elevation', Elevation)
setattr(topologic.Topology, 'Height', Height)

