"""Overloads domain-specific methods onto topologic.Face"""

import topologic
from topologic import Vertex, Edge, Wire, Face, FaceUtility, Cell, CellUtility
from topologist.helpers import create_stl_list
import topologist.ugraph as ugraph


def ByVertices(vertices):
    """Create a Face from an ordered set of Vertices"""
    edges = []
    for i in range(len(vertices) - 1):
        v1 = vertices[i]
        v2 = vertices[i + 1]
        e1 = Edge.ByStartVertexEndVertex(v1, v2)
        edges.append(e1)
    # connect the last vertex to the first one
    v1 = vertices[len(vertices) - 1]
    v2 = vertices[0]
    e1 = Edge.ByStartVertexEndVertex(v1, v2)
    edges.append(e1)
    edges_ptr = create_stl_list(Edge)
    for edge in edges:
        edges_ptr.push_back(edge)
    return Face.ByEdges(edges_ptr)


setattr(topologic.Face, "ByVertices", ByVertices)


def CellsOrdered(self):
    """Front Cell and back Cell, can be None"""
    centroid = list(self.Centroid().Coordinates())
    normal = self.Normal()
    vertex_front = Vertex.ByCoordinates(
        centroid[0] + (normal[0] / 10),
        centroid[1] + (normal[1] / 10),
        centroid[2] + (normal[2] / 10),
    )
    vertex_back = Vertex.ByCoordinates(
        centroid[0] - (normal[0] / 10),
        centroid[1] - (normal[1] / 10),
        centroid[2] - (normal[2] / 10),
    )

    cells = create_stl_list(Cell)
    self.Cells(cells)
    results = [None, None]
    for cell in cells:
        if CellUtility.Contains(cell, vertex_front) == 0:
            results[0] = cell
        elif CellUtility.Contains(cell, vertex_back) == 0:
            results[1] = cell
    return results


def VerticesPerimeter(self, vertices_result):
    """Vertices, tracing the outer perimeter"""
    wires = create_stl_list(Wire)
    self.Wires(wires)
    list(wires)[0].Vertices(vertices_result)
    return vertices_result


def BadNormal(self):
    """Faces on outside of cellcomplex are orientated correctly, but 'outside'
    faces inside the cellcomplex have random orientation"""
    if not self.IsWorld():
        cells = self.CellsOrdered()
        if cells[1].IsOutside() and not cells[0].IsOutside():
            self.Set("badnormal", True)
            return True
    return False


def IsVertical(self):
    normal = self.Normal()
    if abs(normal[2]) < 0.0001:
        return True
    return False


def IsHorizontal(self):
    normal = self.Normal()
    if abs(normal[2]) > 0.9999:
        return True
    return False


def IsUpward(self):
    normal = self.Normal()
    if normal[2] > 0.0:
        return True
    return False


def AxisOuter(self):
    """2D bottom edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    if len(edges) > 0:
        unordered = ugraph.graph()
        for edge in edges:
            start_coor = edge.StartVertex().String()
            end_coor = edge.EndVertex().String()
            unordered.add_edge(
                {start_coor: [end_coor, [edge.StartVertex(), edge.EndVertex(), self]]}
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [ordered.graph[first_edge][1][1], ordered.graph[last_edge][1][0]]
        else:
            return [ordered.graph[first_edge][1][0], ordered.graph[last_edge][1][1]]


def AxisOuterTop(self):
    """2D top edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    if len(edges) > 0:
        unordered = ugraph.graph()
        for edge in edges:
            start_coor = edge.StartVertex().String()
            end_coor = edge.EndVertex().String()
            unordered.add_edge(
                {start_coor: [end_coor, [edge.StartVertex(), edge.EndVertex(), self]]}
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [ordered.graph[last_edge][1][0], ordered.graph[first_edge][1][1]]
        else:
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
    elif len(cells) == 1:
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
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if self.Get("badnormal"):
        return [-normal_stl.X(), -normal_stl.Y(), -normal_stl.Z()]
    else:
        return [normal_stl.X(), normal_stl.Y(), normal_stl.Z()]


def TopLevelConditions(self):
    """Assuming this is a vertical external wall, how do the top edges continue?"""
    result = []
    edges = create_stl_list(Edge)
    self.EdgesTop(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.FacesExternal(faces)
        for (
            face
        ) in faces:  # there should only be one external face (not including self)
            if face.IsSame(self):
                continue
            # top face tilts backward (roof) if normal faces up, forward (soffit) if faces down
            normal = face.Normal()
            condition = "top"
            if abs(normal[2]) < 0.0001:
                condition += "-vertical"
            elif normal[2] > 0.0:
                condition += "-backward"
            else:
                condition += "-forward"
            # top face can be above or below top edge
            if abs(normal[2]) > 0.9999:
                condition += "-level"
            elif face.Centroid().Z() > edge.Centroid().Z():
                condition += "-up"
            else:
                condition += "-down"
            result.append([edge, condition])
    return result


def BottomLevelConditions(self):
    """Assuming this is a vertical external wall, how do the bottom edges continue?"""
    result = []
    edges = create_stl_list(Edge)
    self.EdgesBottom(edges)
    for edge in edges:
        faces = create_stl_list(Face)
        edge.FacesExternal(faces)
        for (
            face
        ) in faces:  # there should only be one external face (not including self)
            if face.IsSame(self):
                continue
            # bottom face tilts forward (roof) if normal faces up, backward (soffit) if faces down
            normal = face.Normal()
            condition = "bottom"
            if abs(normal[2]) < 0.0001:
                condition += "-vertical"
            elif normal[2] > 0.0:
                condition += "-forward"
            else:
                condition += "-backward"
            # bottom face can be above or below bottom edge
            if abs(normal[2]) > 0.9999:
                condition += "-level"
            elif face.Centroid().Z() > edge.Centroid().Z():
                condition += "-up"
            else:
                condition += "-down"
            result.append([edge, condition])
    return result


setattr(topologic.Face, "CellsOrdered", CellsOrdered)
setattr(topologic.Face, "VerticesPerimeter", VerticesPerimeter)
setattr(topologic.Face, "BadNormal", BadNormal)
setattr(topologic.Face, "IsVertical", IsVertical)
setattr(topologic.Face, "IsHorizontal", IsHorizontal)
setattr(topologic.Face, "IsUpward", IsUpward)
setattr(topologic.Face, "AxisOuter", AxisOuter)
setattr(topologic.Face, "AxisOuterTop", AxisOuterTop)
setattr(topologic.Face, "IsInternal", IsInternal)
setattr(topologic.Face, "IsExternal", IsExternal)
setattr(topologic.Face, "IsWorld", IsWorld)
setattr(topologic.Face, "IsOpen", IsOpen)
setattr(topologic.Face, "FaceAbove", FaceAbove)
setattr(topologic.Face, "FaceBelow", FaceBelow)
setattr(topologic.Face, "HorizontalFacesSideways", HorizontalFacesSideways)
setattr(topologic.Face, "Normal", Normal)
setattr(topologic.Face, "TopLevelConditions", TopLevelConditions)
setattr(topologic.Face, "BottomLevelConditions", BottomLevelConditions)
