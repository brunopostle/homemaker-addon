"""Overloads domain-specific methods onto topologic.Cell"""

import topologic
from topologic import Vertex, Edge, Face, Cell, FaceUtility
from topologist.helpers import create_stl_list, el
import topologist.ugraph as ugraph


def FacesTop(self, result_faces_ptr):
    faces_ptr = create_stl_list(Face)
    self.Faces(faces_ptr)
    for face in faces_ptr:
        if (
            face.Elevation() == el(self.Elevation() + self.Height())
            and face.Height() == 0.0
        ):
            result_faces_ptr.push_back(face)


def FacesBottom(self, result_faces_ptr):
    faces_ptr = create_stl_list(Face)
    self.Faces(faces_ptr)
    for face in faces_ptr:
        if face.Elevation() == self.Elevation() and face.Height() == 0.0:
            result_faces_ptr.push_back(face)


def FacesVerticalExternal(self, result_faces_ptr):
    faces_ptr = create_stl_list(Face)
    self.Faces(faces_ptr)
    for face in faces_ptr:
        if face.IsVertical() and face.IsExternal():
            result_faces_ptr.push_back(face)


def CellsAbove(self, topology, result_cells_ptr):
    """Cells (excluding self) connected to top faces of this cell"""
    top_faces_ptr = create_stl_list(Face)
    self.FacesTop(top_faces_ptr)
    for face in top_faces_ptr:
        cells_ptr = create_stl_list(Cell)
        FaceUtility.AdjacentCells(face, topology, cells_ptr)
        for cell in cells_ptr:
            if not cell.IsSame(self):
                result_cells_ptr.push_back(cell)


def CellsBelow(self, topology, result_cells_ptr):
    """Cells (excluding self) connected to bottom faces of this cell"""
    bottom_faces_ptr = create_stl_list(Face)
    self.FacesBottom(bottom_faces_ptr)
    for face in bottom_faces_ptr:
        cells_ptr = create_stl_list(Cell)
        FaceUtility.AdjacentCells(face, topology, cells_ptr)
        for cell in cells_ptr:
            if not cell.IsSame(self):
                result_cells_ptr.push_back(cell)


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
    faces_ptr = create_stl_list(Face)
    self.FacesBottom(faces_ptr)
    for face in faces_ptr:
        result += FaceUtility.Area(face)
    return result


def ExternalWallArea(self):
    result = 0.0
    faces_ptr = create_stl_list(Face)
    self.FacesVerticalExternal(faces_ptr)
    for face in faces_ptr:
        result += FaceUtility.Area(face)
    return result


def Crinkliness(self):
    if self.PlanArea() == 0.0:
        return 0.0
    return self.ExternalWallArea() / self.PlanArea()


def Perimeter(self):
    """2D outline of cell floor, closed, anti-clockwise"""
    elevation = self.Elevation()
    faces_ptr = create_stl_list(Face)
    self.FacesVertical(faces_ptr)
    edges_ptr = create_stl_list(Edge)
    lookup = {}
    for face in faces_ptr:
        if face.Elevation() == elevation:
            edge = face.AxisOuter()
            if edge:
                edges_ptr.push_back(Edge.ByStartVertexEndVertex(edge[0], edge[1]))
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
    if len(list(edges_ptr)) < 3:
        return graph
    try:
        floor = Face.ByEdges(edges_ptr)
    except:
        return graph

    normal = floor.Normal()
    vertices_ptr = create_stl_list(Vertex)
    floor.VerticesPerimeter(vertices_ptr)
    vertices_list = list(vertices_ptr)

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
        cells_ptr = create_stl_list(Cell)
        face.Cells(cells_ptr)
        for cell in cells_ptr:
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
