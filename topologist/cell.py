import topologic
from topologic import Vertex, Edge, Wire, Face, Cell, FaceUtility
from topologist.helpers import create_stl_list, el

def FacesTop(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if(face.Elevation() == el(self.Elevation() + self.Height()) and face.Height() == 0.0):
            faces_result.push_back(face)

def FacesBottom(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if(face.Elevation() == self.Elevation() and face.Height() == 0.0):
            faces_result.push_back(face)

def FacesVerticalExternal(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.IsVertical() and face.IsExternal():
            faces_result.push_back(face)

def CellsAbove(self, topology, cells_result):
    """Cells (excluding self) connected to top faces of this cell"""
    faces_top = create_stl_list(Face)
    self.FacesTop(faces_top)
    for face in faces_top:
        cells = create_stl_list(Cell)
        FaceUtility.AdjacentCells(face, topology, cells)
        for cell in cells:
            if not cell.IsSame(self):
                cells_result.push_back(cell)

def CellsBelow(self, topology, cells_result):
    """Cells (excluding self) connected to bottom faces of this cell"""
    faces_bottom = create_stl_list(Face)
    self.FacesBottom(faces_bottom)
    for face in faces_bottom:
        cells = create_stl_list(Cell)
        FaceUtility.AdjacentCells(face, topology, cells)
        for cell in cells:
            if not cell.IsSame(self):
                cells_result.push_back(cell)

def Usage(self):
    """Type() is taken by Topologic"""
    usage = self.Get('usage')
    if usage:
        return usage
    return 'living'

def IsOutside(self):
    """Cell with outdoor type"""
    usage = self.Usage()
    if usage == 'outdoor' or usage == 'outside' or usage == 'sahn':
        return True
    return False

def PlanArea(self):
    result = 0.0;
    faces = create_stl_list(Face)
    self.FacesBottom(faces)
    for face in faces:
        result += FaceUtility.Area(face)
    return result

def ExternalWallArea(self):
    result = 0.0;
    faces = create_stl_list(Face)
    self.FacesVerticalExternal(faces)
    for face in faces:
        result += FaceUtility.Area(face)
    return result

def Crinkliness(self):
    if self.PlanArea() == 0.0:
        return 0.0
    return self.ExternalWallArea() / self.PlanArea()

def Perimeter(self):
    """2D outline of cell floor, closed, anti-clockwise"""
    # FIXME process of creating floor-Face/Wire loses valid wall Vertices and Faces
    # this needs to return a ugraph instead of a list of unconnected Vertices
    elevation = self.Elevation()
    faces = create_stl_list(Face)
    self.FacesVertical(faces)
    edges = create_stl_list(Edge)
    for face in faces:
        if face.Elevation() == elevation:
            edge = face.AxisOuter()
            if edge:
                edges.push_back(Edge.ByStartVertexEndVertex(edge[0], edge[1]))
    if len(edges) < 3:
        return []
    # FIXME molior stair requires a four sided space, but Perimeter can have colinear edges
    floor = Face.ByEdges(edges)
    normal = floor.Normal()

    # FIXME should support doughnut shaped rooms
    wires = create_stl_list(Wire)
    floor.Wires(wires)
    for wire in wires:
        vertices = create_stl_list(Vertex)
        wire.Vertices(vertices)
        if len(vertices) < 3:
            continue
        elif normal.Z() > 0.9999:
            # good, loop is anticlockwise
            return vertices
        elif normal.Z() < -0.9999:
            vertices_reversed = create_stl_list(Vertex)
            vertices_list = list(vertices)
            vertices_list.reverse()
            for vertex in vertices_list:
                vertices_reversed.push_back(vertex)
            return vertices_reversed
        else:
            return []

setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
setattr(topologic.Cell, 'FacesVerticalExternal', FacesVerticalExternal)
setattr(topologic.Cell, 'CellsAbove', CellsAbove)
setattr(topologic.Cell, 'CellsBelow', CellsBelow)
setattr(topologic.Cell, 'Usage', Usage)
setattr(topologic.Cell, 'IsOutside', IsOutside)
setattr(topologic.Cell, 'PlanArea', PlanArea)
setattr(topologic.Cell, 'ExternalWallArea', ExternalWallArea)
setattr(topologic.Cell, 'Crinkliness', Crinkliness)
setattr(topologic.Cell, 'Perimeter', Perimeter)
