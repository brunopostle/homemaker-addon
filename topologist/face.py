import cppyy
import topologic
from topologic import Edge, Face, FaceUtility

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
    edges_ptr = cppyy.gbl.std.list[topologic.Edge.Ptr]()
    for edge in edges:
        edges_ptr.push_back(edge)
    return Face.ByEdges(edges_ptr)

setattr(topologic.Face, 'ByVertices', ByVertices)

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
    cells_ptr = cppyy.gbl.std.list[topologic.Cell.Ptr]()
    self.Cells(cells_ptr)
    if len(cells_ptr) == 2:
        for cell in cells_ptr:
            if cell.IsOutside():
                return False
        return True
    return False

def IsExternal(self):
    """Face between indoor cell and (outdoor cell or world)"""
    cells_ptr = cppyy.gbl.std.list[topologic.Cell.Ptr]()
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
    cells_ptr = cppyy.gbl.std.list[topologic.Cell.Ptr]()
    self.Cells(cells_ptr)
    if len(cells_ptr) == 1:
        return True
    return False

def IsOpen(self):
    """Face on outdoor cell on outside of mesh"""
    cells_ptr = cppyy.gbl.std.list[topologic.Cell.Ptr]()
    self.Cells(cells_ptr)
    if len(cells_ptr) == 1:
        for cell in cells_ptr:
            if cell.IsOutside():
                return True
    return False

def Normal(self):
    return FaceUtility.NormalAtParameters(self, 0.5, 0.5)

setattr(topologic.Face, 'IsVertical', IsVertical)
setattr(topologic.Face, 'IsHorizontal', IsHorizontal)
setattr(topologic.Face, 'IsInternal', IsInternal)
setattr(topologic.Face, 'IsExternal', IsExternal)
setattr(topologic.Face, 'IsWorld', IsWorld)
setattr(topologic.Face, 'IsOpen', IsOpen)
setattr(topologic.Face, 'Normal', Normal)
