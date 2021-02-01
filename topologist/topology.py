import topologic
from topologic import Vertex, Edge, Wire, Face
from topologist.helpers import create_stl_list

def FacesVertical(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsVertical():
            faces_result.push_back(face)

def FacesHorizontal(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_result.push_back(face)

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

def EdgesTop(self, edges_result):
    """A list of horizontal edges at the highest level of this face"""
    edges = create_stl_list(Edge)
    self.Edges(edges)
    for edge in edges:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        level = self.Elevation() + self.Height()
        if vertex_start.Z() == level and vertex_end.Z() == level:
            edges_result.push_back(edge)

def EdgesBottom(self, edges_result):
    """A list of horizontal edges at the lowest level of this face"""
    edges = create_stl_list(Edge)
    self.Edges(edges)
    for edge in edges:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        level = self.Elevation()
        if vertex_start.Z() == level and vertex_end.Z() == level:
            edges_result.push_back(edge)

def AxisOuter(self):
    """2D bottom edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    if len(edges) == 0: return
    wire = Wire.ByEdges(edges)
    vertices_stl = create_stl_list(Vertex)
    wire.Vertices(vertices_stl)
    vertices = list(vertices_stl)
    return Edge.ByStartVertexEndVertex(vertices[0], vertices[-1])

def AxisOuterTop(self):
    """2D top edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    if len(edges) == 0: return
    wire = Wire.ByEdges(edges)
    vertices_stl = create_stl_list(Vertex)
    wire.Vertices(vertices_stl)
    vertices = list(vertices_stl)
    return Edge.ByStartVertexEndVertex(vertices[-1], vertices[0])

setattr(topologic.Topology, 'FacesVertical', FacesVertical)
setattr(topologic.Topology, 'FacesHorizontal', FacesHorizontal)
setattr(topologic.Topology, 'Elevation', Elevation)
setattr(topologic.Topology, 'Height', Height)
setattr(topologic.Topology, 'EdgesTop', EdgesTop)
setattr(topologic.Topology, 'EdgesBottom', EdgesBottom)
setattr(topologic.Topology, 'AxisOuter', AxisOuter)
setattr(topologic.Topology, 'AxisOuterTop', AxisOuterTop)
