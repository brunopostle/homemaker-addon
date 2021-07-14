"""Overloads domain-specific methods onto topologic.Cell"""

import topologic
from topologic import Vertex, Edge, Face, Cell, FaceUtility
from topologist.helpers import create_stl_list, el
import topologist.ugraph as ugraph


def FacesTop(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if (
            face.Elevation() == el(self.Elevation() + self.Height())
            and face.Height() == 0.0
        ):
            faces_result.push_back(face)


def FacesBottom(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if face.Elevation() == self.Elevation() and face.Height() == 0.0:
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
    usage = self.Get("usage")
    if usage:
        return usage
    return "living"


def IsOutside(self):
    """Cell with outdoor type"""
    usage = self.Usage()
    if usage == "outdoor" or usage == "outside" or usage == "sahn":
        return True
    return False


def PlanArea(self):
    result = 0.0
    faces = create_stl_list(Face)
    self.FacesBottom(faces)
    for face in faces:
        result += FaceUtility.Area(face)
    return result


def ExternalWallArea(self):
    result = 0.0
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
    elevation = self.Elevation()
    faces = create_stl_list(Face)
    self.FacesVertical(faces)
    edges = create_stl_list(Edge)
    lookup = {}
    for face in faces:
        if face.Elevation() == elevation:
            edge = face.AxisOuter()
            if edge:
                edges.push_back(Edge.ByStartVertexEndVertex(edge[0], edge[1]))
                # process of creating a wire loses all references to original cellcomplex, stash
                lookup[edge[0].CoorAsString() + " " + edge[1].CoorAsString()] = [
                    edge[0],
                    edge[1],
                    face,
                ]
                lookup[edge[1].CoorAsString() + " " + edge[0].CoorAsString()] = [
                    edge[1],
                    edge[0],
                    face,
                ]

    graph = ugraph.graph()

    # edges are in no particular order or direction
    if len(list(edges)) < 3:
        return graph
    try:
        floor = Face.ByEdges(edges)
    except:
        return graph

    normal = floor.Normal()
    vertices = create_stl_list(Vertex)
    floor.VerticesPerimeter(vertices)
    vertices_list = list(vertices)

    clockwise = False
    if normal[2] < 0.0:
        clockwise = True
    for i in range(len(vertices_list)):
        if clockwise:
            start = vertices_list[i]
            end = vertices_list[i - 1]
        else:
            start = vertices_list[i - 1]
            end = vertices_list[i]
        start_coor = start.CoorAsString()
        end_coor = end.CoorAsString()
        refs = lookup[start_coor + " " + end_coor]

        outer_cell = None
        face = refs[2]
        cells = create_stl_list(Cell)
        face.Cells(cells)
        for cell in cells:
            if not cell.IsSame(self):
                outer_cell = cell
        graph.add_edge(
            {start_coor: [end_coor, [refs[0], refs[1], refs[2], self, outer_cell]]}
        )
    # returning the first cycle will do weird things with doughnut shaped rooms
    return graph.find_paths()[0]


setattr(topologic.Cell, "FacesTop", FacesTop)
setattr(topologic.Cell, "FacesBottom", FacesBottom)
setattr(topologic.Cell, "FacesVerticalExternal", FacesVerticalExternal)
setattr(topologic.Cell, "CellsAbove", CellsAbove)
setattr(topologic.Cell, "CellsBelow", CellsBelow)
setattr(topologic.Cell, "Usage", Usage)
setattr(topologic.Cell, "IsOutside", IsOutside)
setattr(topologic.Cell, "PlanArea", PlanArea)
setattr(topologic.Cell, "ExternalWallArea", ExternalWallArea)
setattr(topologic.Cell, "Crinkliness", Crinkliness)
setattr(topologic.Cell, "Perimeter", Perimeter)
