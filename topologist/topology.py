import topologic
from topologic import Vertex, Face
from topologist.helpers import create_stl_list

def FacesVertical(self):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if face.IsVertical():
            faces_result.append(face)
    return faces_result

def FacesHorizontal(self):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_result.append(face)
    return faces_result

def Elevation(self):
    lowest = 9999999.9
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return lowest

def Height(self):
    highest = -9999999.9
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    for vertex in vertices:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return highest - self.Elevation()

setattr(topologic.Topology, 'FacesVertical', FacesVertical)
setattr(topologic.Topology, 'FacesHorizontal', FacesHorizontal)
setattr(topologic.Topology, 'Elevation', Elevation)
setattr(topologic.Topology, 'Height', Height)
