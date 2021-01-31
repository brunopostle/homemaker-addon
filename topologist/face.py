import topologic
from topologic import Edge, Face, FaceUtility, Cell
from topologist.helpers import create_stl_list

def ByVertices(vertices):
    edges = []
    for i in range(len(vertices)-1):
        v1 = vertices[i]
        v2 = vertices[i+1]
        e1 = Edge.ByStartVertexEndVertex(v1, v2)
        edges.append(e1)
    # connect the last vertex to the first one
    v1 = vertices[len(vertices)-1]
    v2 = vertices[0]
    e1 = Edge.ByStartVertexEndVertex(v1, v2)
    edges.append(e1)
    edges_ptr = create_stl_list(Edge)
    for edge in edges:
        edges_ptr.push_back(edge)
    return Face.ByEdges(edges_ptr)

setattr(topologic.Face, 'ByVertices', ByVertices)

def AxisOuter(self):
    """2D bottom edge of a vertical face, for external walls, anti-clockwise in plan"""
    # TODO
    pass

def AxisOuterTop(self):
    """2D top edge of a vertical face, for external walls, anti-clockwise in plan"""
    # TODO
    pass

def Types(self):
    """Cell types associated with this face, 1 or 2 items"""
    # TODO
    pass

def TypeInside(self):
    """Inside cell type associated with this face, otherwise 'Outside'"""
    # TODO
    pass

def IsVertical(self):
    normal = self.Normal()
    if abs(normal.Z()) < 0.0001:
        return True
    return False

def IsHorizontal(self):
    normal = self.Normal()
    if abs(normal.Z()) > 0.9999:
        return True
    return False

def IsInternal(self):
    """Face between two indoor cells"""
    cells_ptr = create_stl_list(Cell)
    self.Cells(cells_ptr)
    if len(cells_ptr) == 2:
        for cell in cells_ptr:
            if cell.IsOutside():
                return False
        return True
    return False

def IsExternal(self):
    """Face between indoor cell and (outdoor cell or world)"""
    cells_ptr = create_stl_list(Cell)
    self.Cells(cells_ptr)
    cells = []
    for cell in cells_ptr:
        cells.append(cell)
    if len(cells) == 2:
        if cells[0].IsOutside() and not cells[1].IsOutside():
            return True
        if cells[1].IsOutside() and not cells[0].IsOutside():
            return True
    else:
        if not cells[0].IsOutside():
            return True
    return False

def IsWorld(self):
    """Face on outside of mesh"""
    cells_ptr = create_stl_list(Cell)
    self.Cells(cells_ptr)
    if len(cells_ptr) == 1:
        return True
    return False

def IsOpen(self):
    """Face on outdoor cell on outside of mesh"""
    cells_ptr = create_stl_list(Cell)
    self.Cells(cells_ptr)
    if len(cells_ptr) == 1:
        for cell in cells_ptr:
            if cell.IsOutside():
                return True
    return False

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

def IsFaceAbove(self):
    """Does vertical face have a vertical face attached to a horizontal top?"""
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.Faces(faces)
        for face in faces:
            if face.IsVertical() and not face.IsSame(self):
                return True
    return False

def IsFaceBelow(self):
    """Does vertical face have a vertical face attached to a horizontal bottom?"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.Faces(faces)
        for face in faces:
            if face.IsVertical() and not face.IsSame(self):
                return True
    return False

def HorizontalFacesSideways(self):
    """Which horizontal faces are attached to the bottom of this vertical face?"""
    # TODO
    pass

def Normal(self):
    return FaceUtility.NormalAtParameters(self, 0.5, 0.5)

setattr(topologic.Face, 'AxisOuter', AxisOuter)
setattr(topologic.Face, 'AxisOuterTop', AxisOuterTop)
setattr(topologic.Face, 'Types', Types)
setattr(topologic.Face, 'TypeInside', TypeInside)
setattr(topologic.Face, 'IsVertical', IsVertical)
setattr(topologic.Face, 'IsHorizontal', IsHorizontal)
setattr(topologic.Face, 'IsInternal', IsInternal)
setattr(topologic.Face, 'IsExternal', IsExternal)
setattr(topologic.Face, 'IsWorld', IsWorld)
setattr(topologic.Face, 'IsOpen', IsOpen)
setattr(topologic.Face, 'EdgesTop', EdgesTop)
setattr(topologic.Face, 'EdgesBottom', EdgesBottom)
setattr(topologic.Face, 'IsFaceAbove', IsFaceAbove)
setattr(topologic.Face, 'IsFaceBelow', IsFaceBelow)
setattr(topologic.Face, 'HorizontalFacesSideways', HorizontalFacesSideways)
setattr(topologic.Face, 'Normal', Normal)
