import topologic
from topologic import Edge, Face, FaceUtility, Cell
from topologist.helpers import create_stl_list, vertex_string
from topologist import ugraph

def ByVertices(vertices):
    """Create a Face from an ordered set of Vertices"""
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

def Usages(self):
    """Cell types associated with this face, 1 or 2 items"""
    results = []
    cells = create_stl_list(Cell)
    self.Cells(cells)
    for cell in cells:
        results.append(cell.Usage())
    return results

def UsageInside(self):
    """Inside cell type associated with this face, otherwise 'Outside'"""
    cells = create_stl_list(Cell)
    self.Cells(cells)
    for cell in cells:
        if not cell.IsOutside():
            return cell.Usage()
    return 'Outside'

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

def AxisOuter(self):
    """2D bottom edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    if len(edges) == 0: return None
    unordered = ugraph.graph()
    for edge in edges:
        start_coor = vertex_string(edge.StartVertex())
        end_coor = vertex_string(edge.EndVertex())
        unordered.add_edge({start_coor: [end_coor, [edge.StartVertex(), edge.EndVertex(), self]]})
    ordered = unordered.find_chains()[0]
    ordered_edges = ordered.edges()
    first_edge = ordered_edges[0][0]
    last_edge = ordered_edges[-1][0]
    return [ordered.graph[first_edge][1][0], ordered.graph[last_edge][1][1]]

def AxisOuterTop(self):
    """2D top edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    if len(edges) == 0: return None
    unordered = ugraph.graph()
    for edge in edges:
        start_coor = vertex_string(edge.StartVertex())
        end_coor = vertex_string(edge.EndVertex())
        unordered.add_edge({start_coor: [end_coor, [edge.StartVertex(), edge.EndVertex(), self]]})
    ordered = unordered.find_chains()[0]
    ordered_edges = ordered.edges()
    first_edge = ordered_edges[0][0]
    last_edge = ordered_edges[-1][0]
    return [ordered.graph[last_edge][1][1], ordered.graph[first_edge][1][0]]

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

def FaceAbove(self):
    """Does vertical face have a vertical face attached to a horizontal top?"""
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.Faces(faces)
        for face in faces:
            if face.IsVertical() and not face.IsSame(self):
                return face
    return None

def FaceBelow(self):
    """Does vertical face have a vertical face attached to a horizontal bottom?"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.Faces(faces)
        for face in faces:
            if face.IsVertical() and not face.IsSame(self):
                return face
    return None

def HorizontalFacesSideways(self, faces_result):
    """Which horizontal faces are attached to the bottom of this vertical face?"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.Faces(faces)
        for face in faces:
            if face.IsHorizontal() and not face.IsSame(self):
                faces_result.push_back(face)
    return faces_result

def Normal(self):
    return FaceUtility.NormalAtParameters(self, 0.5, 0.5)

setattr(topologic.Face, 'Usages', Usages)
setattr(topologic.Face, 'UsageInside', UsageInside)
setattr(topologic.Face, 'IsVertical', IsVertical)
setattr(topologic.Face, 'IsHorizontal', IsHorizontal)
setattr(topologic.Face, 'AxisOuter', AxisOuter)
setattr(topologic.Face, 'AxisOuterTop', AxisOuterTop)
setattr(topologic.Face, 'IsInternal', IsInternal)
setattr(topologic.Face, 'IsExternal', IsExternal)
setattr(topologic.Face, 'IsWorld', IsWorld)
setattr(topologic.Face, 'IsOpen', IsOpen)
setattr(topologic.Face, 'FaceAbove', FaceAbove)
setattr(topologic.Face, 'FaceBelow', FaceBelow)
setattr(topologic.Face, 'HorizontalFacesSideways', HorizontalFacesSideways)
setattr(topologic.Face, 'Normal', Normal)
