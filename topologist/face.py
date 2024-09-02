"""Overloads domain-specific methods onto topologic_core.Face"""

from functools import lru_cache
import math
import topologic_core
from topologic_core import Vertex, Edge, Face, Cluster, FaceUtility, CellUtility
from .helpers import el
from . import ugraph


def ByVertices(vertices):
    """Create a Face from an ordered set of Vertices"""
    edges_ptr = []
    for i in range(len(vertices) - 1):
        v1 = vertices[i]
        v2 = vertices[i + 1]
        e1 = Edge.ByStartVertexEndVertex(v1, v2)
        edges_ptr.append(e1)
    # connect the last vertex to the first one
    v1 = vertices[len(vertices) - 1]
    v2 = vertices[0]
    e1 = Edge.ByStartVertexEndVertex(v1, v2)
    edges_ptr.append(e1)
    return Face.ByEdges(edges_ptr)


setattr(topologic_core.Face, "ByVertices", ByVertices)


@lru_cache(maxsize=256)
def CellsOrdered(self, host_topology):
    """Front Cell and back Cell, can be [None, None]"""
    centroid = FaceUtility.InternalVertex(self, 0.001).Coordinates()
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

    results = [None, None]
    if host_topology:
        cells_ptr = self.Cells_Cached(host_topology)
        for cell in cells_ptr:
            if CellUtility.Contains(cell, vertex_front, 0.001) == 0:
                results[0] = cell
            elif CellUtility.Contains(cell, vertex_back, 0.001) == 0:
                results[1] = cell
    return results


def VerticesPerimeter(self, vertices_ptr):
    """List of Vertices tracing the outer perimeter of this Face"""
    return self.ExternalBoundary().Vertices(None, vertices_ptr)


def BadNormal(self, cellcomplex):
    """Faces on outside of CellComplex are orientated correctly, but 'outside'
    Faces inside the CellComplex have random orientation. Tags with 'badnormal'
    if the Face doesn't face 'out'"""
    if not self.IsWorld(cellcomplex):
        cells = self.CellsOrdered(cellcomplex)
        if cells[0] is None or cells[1] is None:
            self.Set("badnormal", True)
            return True
        if cells[1].IsOutside() and not cells[0].IsOutside():
            self.Set("badnormal", True)
            return True
    return False


def IsVertical(self):
    """Is this Face vertical?"""
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if abs(normal_stl[2]) < 0.0001:
        return True
    return False


def IsHorizontal(self):
    """Is this Face horizontal?"""
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if abs(normal_stl[2]) > 0.9999:
        return True
    return False


def IsUpward(self):
    """Does the normal of this Face point up?"""
    normal = self.Normal()
    if normal[2] > 0.0:
        return True
    return False


def AxisOuter(self):
    """2D bottom edge of a vertical Face as a pair of Vertices. Anti-clockwise for external walls"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    if len(edges_ptr) > 0:
        unordered = ugraph.graph()
        for edge in edges_ptr:
            start_coor = edge.StartVertex().CoorAsString()
            end_coor = edge.EndVertex().CoorAsString()
            unordered.add_edge(
                {
                    start_coor: [
                        end_coor,
                        {
                            "start_vertex": edge.StartVertex(),
                            "end_vertex": edge.EndVertex(),
                        },
                    ]
                }
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [
                ordered.graph[first_edge][1]["end_vertex"],
                ordered.graph[last_edge][1]["start_vertex"],
            ]
        else:
            return [
                ordered.graph[first_edge][1]["start_vertex"],
                ordered.graph[last_edge][1]["end_vertex"],
            ]


# FIXME doesn't appear to be in use
def AxisOuterTop(self):
    """2D top edge of a vertical Face as a pair of Vertices. Anti-clockwise for external walls"""
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    if len(edges_ptr) > 0:
        unordered = ugraph.graph()
        for edge in edges_ptr:
            start_coor = edge.StartVertex().CoorAsString()
            end_coor = edge.EndVertex().CoorAsString()
            unordered.add_edge(
                {
                    start_coor: [
                        end_coor,
                        {
                            "start_vertex": edge.StartVertex(),
                            "end_vertex": edge.EndVertex(),
                        },
                    ]
                }
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [
                ordered.graph[last_edge][1]["start_vertex"],
                ordered.graph[first_edge][1]["end_vertex"],
            ]
        else:
            return [
                ordered.graph[last_edge][1]["end_vertex"],
                ordered.graph[first_edge][1]["start_vertex"],
            ]


@lru_cache(maxsize=256)
def IsInternal(self, host_topology):
    """Is this Face between two inside Cells?"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 2:
        for cell in cells_ptr:
            if cell.IsOutside():
                return False
        return True
    return False


@lru_cache(maxsize=256)
def IsExternal(self, host_topology):
    """Is this Face between an inside Cell and outside Cell (or world)?"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 2:
        if cells_ptr[0].IsOutside() and not cells_ptr[1].IsOutside():
            return True
        if cells_ptr[1].IsOutside() and not cells_ptr[0].IsOutside():
            return True
    elif len(cells_ptr) == 1:
        if not cells_ptr[0].IsOutside():
            return True
    return False


@lru_cache(maxsize=256)
def IsWorld(self, host_topology):
    """Is this Face on the outside of the mesh? i.e. does it adjoin only one Cell?"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 1:
        return True
    return False


@lru_cache(maxsize=256)
def IsOpen(self, host_topology):
    """Is this Face on the outside of the mesh and adjoining an 'outside' Cell?"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 1:
        for cell in cells_ptr:
            if cell.IsOutside():
                return True
    return False


# FIXME doesn't appear to be in use
def FaceAbove(self, host_topology):
    """Is there a vertical Face attached above to a horizontal top Edge? Returns None or a single Face"""
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    for edge in edges_ptr:
        faces_ptr = edge.Faces_Cached(host_topology)
        for face in faces_ptr:
            if face.IsVertical() and not face.IsSame(self):
                return face
    return None


def FacesBelow(self, host_topology):
    """Returns a list of Faces attached below to a horizontal bottom Edge?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result = []
    for edge in edges_ptr:
        faces_below = edge.FacesBelow(host_topology)
        if faces_below:
            result.extend(faces_below)
    return result


def CellsBelow(self, host_topology):
    """Returns a list of Cells attached below to a horizontal bottom Edge?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result = []
    for edge in edges_ptr:
        cells_below = edge.CellsBelow(host_topology)
        if cells_below:
            result.extend(cells_below)
    return result


def CellAbove(self, host_topology):
    """Is this Face a floor for a Cell above? return it"""
    if not self.IsVertical():
        cells = self.Cells_Cached(host_topology)
        if len(cells) == 2:
            if cells[0].Centroid().Z() > cells[1].Centroid().Z():
                return cells[0]
            return cells[1]
        elif len(cells) == 1 and cells[0].Centroid().Z() > self.Centroid().Z():
            return cells[0]
    return None


def CellBelow(self, host_topology):
    """Is this Face a ceiling for a Cell below? return it"""
    if not self.IsVertical():
        cells = self.Cells_Cached(host_topology)
        if len(cells) == 2:
            if cells[0].Centroid().Z() < cells[1].Centroid().Z():
                return cells[0]
            return cells[1]
        elif len(cells) == 1 and cells[0].Centroid().Z() < self.Centroid().Z():
            return cells[0]
    return None


# FIXME doesn't appear to be in use
def HorizontalFacesSideways(self, host_topology):
    """Which horizontal faces are attached to the bottom Edges of this Face?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result_faces_ptr = []
    for edge in edges_ptr:
        faces_ptr = edge.Faces_Cached(host_topology)
        for face in faces_ptr:
            if face.IsHorizontal() and not face.IsSame(self):
                result_faces_ptr.append(face)
    return result_faces_ptr


def Normal(self):
    """A normal for this Face as a three element list, but flipped if this Face is tagged with 'badnormal'"""
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if self.Get("badnormal"):
        return [-normal_stl[0], -normal_stl[1], -normal_stl[2]]
    else:
        return [normal_stl[0], normal_stl[1], normal_stl[2]]


def Plane(self):
    """Return A, B, C, D plane parameters"""
    vertices = []
    self.Vertices(None, vertices)
    point = vertices[0].Coordinates()
    A, B, C = self.Normal()
    D = 0 - (A * point[0] + B * point[1] + C * point[2])
    return [A, B, C, D]


def IsCoplanar(self, face, k=0.01):
    """Check if face is coplanar"""
    plane = self.Plane()
    other = face.Plane()
    if (
        abs(plane[0] - other[0]) < k
        and abs(plane[1] - other[1]) < k
        and abs(plane[2] - other[2]) < k
        and abs(plane[3] - other[3]) < k
    ):
        return True
    if (
        abs(plane[0] + other[0]) < k
        and abs(plane[1] + other[1]) < k
        and abs(plane[2] + other[2]) < k
        and abs(plane[3] + other[3]) < k
    ):
        return True
    return False


def TopLevelConditions(self, host_topology):
    """Assuming this is a vertical external wall, how do the top edges continue?"""
    # TODO traces where face above is open
    result = []
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    for edge in edges_ptr:
        faces_ptr = edge.FacesWorld(host_topology)
        for (
            face
        ) in faces_ptr:  # there should only be one external face (not including self)
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


def BottomLevelConditions(self, host_topology):
    """Assuming this is a vertical external wall, how do the bottom edges continue?
    Result is a list of [Edge, condition] pairs"""
    # TODO traces where face below is open
    result = []
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    for edge in edges_ptr:
        # FIXME FacesWorld() doesn't account for external walls facing outside cells
        faces_ptr = edge.FacesWorld(host_topology)
        for (
            face
        ) in faces_ptr:  # there should only be one external face (not including self)
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


def EdgesTop(self, result_edges_ptr):
    """A list of horizontal edges at the highest level of this face"""
    edges_ptr = []
    self.Edges(None, edges_ptr)
    level = el(self.Elevation() + self.Height())
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            result_edges_ptr.append(edge)


def EdgesBottom(self, result_edges_ptr):
    """A list of horizontal edges at the lowest level of this face"""
    edges_ptr = []
    self.Edges(None, edges_ptr)
    level = self.Elevation()
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            result_edges_ptr.append(edge)


def EdgesCrop(self, result_edges_ptr):
    """Which edges are not vertical or top/bottom?"""
    edges_ptr = []
    self.ExternalBoundary().Edges(None, edges_ptr)
    bottom = self.Elevation()
    top = el(self.Elevation() + self.Height())
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == top and el(vertex_end.Z()) == top:
            continue
        elif el(vertex_start.Z()) == bottom and el(vertex_end.Z()) == bottom:
            continue
        elif edge.IsVertical():
            continue
        result_edges_ptr.append(edge)


def ParallelSlice(self, inc=0.45, radians=0.0, origin=[0.0, 0.0]):
    """Crop a face with parallel lines. Returns a list of cropped Faces and a list of Edges between them"""
    vertices = []
    self.Vertices(None, vertices)
    minx = min(node.Coordinates()[0] for node in vertices)
    maxx = max(node.Coordinates()[0] for node in vertices)
    miny = min(node.Coordinates()[1] for node in vertices)
    maxy = max(node.Coordinates()[1] for node in vertices)

    # create Topologic Edges for slicing the Face
    # FIXME fixx and fixy adjustment only works for orthogonal angles
    cutting_edges = []
    if abs(math.tan(radians)) > 1.0:
        shift = (maxy - miny) / math.tan(radians)
        incx = inc / abs(math.sin(radians))
        fixx = (minx - origin[0]) % incx
        x = minx - abs(shift) - fixx
        while x < maxx + abs(shift):
            cutting_edges.append(
                Edge.ByStartVertexEndVertex(
                    Vertex.ByCoordinates(x + incx, miny, 0.0),
                    Vertex.ByCoordinates(x + incx + shift, maxy, 0.0),
                )
            )
            x += incx
    else:
        shift = (maxx - minx) * math.tan(radians)
        incy = inc / abs(math.cos(radians))
        fixy = (miny - origin[1]) % incy
        y = miny - abs(shift) - fixy
        while y < maxy + abs(shift):
            cutting_edges.append(
                Edge.ByStartVertexEndVertex(
                    Vertex.ByCoordinates(minx, y + incy, 0.0),
                    Vertex.ByCoordinates(maxx, y + incy + shift, 0.0),
                )
            )
            y += incy

    shell = self.Slice(Cluster.ByTopologies(cutting_edges))
    topologic_faces = []
    shell.Faces(None, topologic_faces)
    topologic_edges = []
    shell.Edges(None, topologic_edges)
    cropped_edges = []
    for topologic_edge in topologic_edges:
        myfaces = []
        topologic_edge.Faces(shell, myfaces)
        if len(myfaces) == 2:
            cropped_edges.append(topologic_edge)
    return topologic_faces, cropped_edges


setattr(topologic_core.Face, "CellsOrdered", CellsOrdered)
setattr(topologic_core.Face, "VerticesPerimeter", VerticesPerimeter)
setattr(topologic_core.Face, "BadNormal", BadNormal)
setattr(topologic_core.Face, "IsVertical", IsVertical)
setattr(topologic_core.Face, "IsHorizontal", IsHorizontal)
setattr(topologic_core.Face, "IsUpward", IsUpward)
setattr(topologic_core.Face, "AxisOuter", AxisOuter)
setattr(topologic_core.Face, "AxisOuterTop", AxisOuterTop)
setattr(topologic_core.Face, "IsInternal", IsInternal)
setattr(topologic_core.Face, "IsExternal", IsExternal)
setattr(topologic_core.Face, "IsWorld", IsWorld)
setattr(topologic_core.Face, "IsOpen", IsOpen)
setattr(topologic_core.Face, "FaceAbove", FaceAbove)
setattr(topologic_core.Face, "FacesBelow", FacesBelow)
setattr(topologic_core.Face, "CellsBelow", CellsBelow)
setattr(topologic_core.Face, "CellAbove", CellAbove)
setattr(topologic_core.Face, "CellBelow", CellBelow)
setattr(topologic_core.Face, "HorizontalFacesSideways", HorizontalFacesSideways)
setattr(topologic_core.Face, "Normal", Normal)
setattr(topologic_core.Face, "Plane", Plane)
setattr(topologic_core.Face, "IsCoplanar", IsCoplanar)
setattr(topologic_core.Face, "TopLevelConditions", TopLevelConditions)
setattr(topologic_core.Face, "BottomLevelConditions", BottomLevelConditions)
setattr(topologic_core.Face, "EdgesTop", EdgesTop)
setattr(topologic_core.Face, "EdgesBottom", EdgesBottom)
setattr(topologic_core.Face, "EdgesCrop", EdgesCrop)
setattr(topologic_core.Face, "ParallelSlice", ParallelSlice)
