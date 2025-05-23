"""Overloads domain-specific methods onto topologic_core.Cell"""

import topologic_core
from topologic_core import Edge, Face, FaceUtility
from .helpers import el
from . import ugraph


def FacesTop(self, result_faces_ptr):
    """List of horizontal Faces at the highest level of this Cell"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        if (
            face.Elevation() == el(self.Elevation() + self.Height())
            and face.Height() == 0.0
        ):
            result_faces_ptr.append(face)


def FacesBottom(self, result_faces_ptr):
    """List of horizontal Faces at the lowest level of this Cell"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        if face.Elevation() == self.Elevation() and face.Height() == 0.0:
            result_faces_ptr.append(face)


def FacesVerticalExternal(self, cellcomplex, result_faces_ptr):
    """List of vertical external Faces"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        if face.IsVertical() and face.IsExternal(cellcomplex):
            result_faces_ptr.append(face)


def CellsAbove(self, topology, result_cells_ptr):
    """Cells (excluding self) connected to horizontal Faces at the top of this Cell"""
    top_faces_ptr = []
    self.FacesTop(top_faces_ptr)
    for face in top_faces_ptr:
        cells_ptr = []
        FaceUtility.AdjacentCells(face, topology, cells_ptr)
        for cell in cells_ptr:
            if not cell.IsSame(self):
                result_cells_ptr.append(cell)


def CellsBelow(self, topology, result_cells_ptr):
    """Cells (excluding self) connected to horizontal Faces at the bottom of this cell"""
    bottom_faces_ptr = []
    self.FacesBottom(bottom_faces_ptr)
    for face in bottom_faces_ptr:
        cells_ptr = []
        FaceUtility.AdjacentCells(face, topology, cells_ptr)
        for cell in cells_ptr:
            if not cell.IsSame(self):
                result_cells_ptr.append(cell)


def Usage(self):
    """What kind of room or space is this (Type() is taken by Topologic)"""
    usage = self.Get("usage")
    if usage:
        return usage
    return "living"


def IsOutside(self):
    """Is this Cell outside? i.e. usage is 'outside' or 'sahn'"""
    usage = self.Usage()
    if usage == "outdoor" or usage == "outside" or usage == "sahn":
        return True
    return False


def PlanArea(self):
    """Surface area of horizontal Faces at the bottom of this Cell"""
    result = 0.0
    faces_ptr = []
    self.FacesBottom(faces_ptr)
    for face in faces_ptr:
        result += FaceUtility.Area(face)
    return result


def ExternalWallArea(self, cellcomplex):
    """Surface area of external vertical Faces"""
    result = 0.0
    faces_ptr = []
    self.FacesVerticalExternal(cellcomplex, faces_ptr)
    for face in faces_ptr:
        # FIXME 'blank' stylename shouldn't be magic like this
        if face.Get("stylename") == "blank":
            continue
        result += FaceUtility.Area(face)
    return result


def Crinkliness(self, cellcomplex):
    """ExternalWallArea() / PlanArea()"""
    plan_area = self.PlanArea()
    if plan_area == 0.0:
        return 0.0
    return self.ExternalWallArea(cellcomplex) / plan_area


def Perimeter(self, host_topology):
    """2D outline of Cell vertical walls, closed, anti-clockwise. Result is a ugraph graph"""
    elevation = self.Elevation()
    faces_ptr = []
    self.FacesVertical(faces_ptr)
    edges_ptr = []
    lookup = {}
    for face in faces_ptr:
        if face.Elevation() == elevation:
            edge = face.AxisOuter()
            if edge:
                edges_ptr.append(Edge.ByStartVertexEndVertex(edge[0], edge[1]))
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
    if len(edges_ptr) < 3:
        return graph
    try:
        floor = Face.ByEdges(edges_ptr)
    except RuntimeError:
        return graph

    normal = floor.Normal()
    vertices_ptr = []
    floor.VerticesPerimeter(vertices_ptr)

    clockwise = False
    if normal[2] < 0.0:
        clockwise = True
    for i in range(len(vertices_ptr)):
        if clockwise:
            start = vertices_ptr[i]
            end = vertices_ptr[i - 1]
        else:
            start = vertices_ptr[i - 1]
            end = vertices_ptr[i]
        start_coor = start.CoorAsString()
        end_coor = end.CoorAsString()
        refs = lookup[start_coor + " " + end_coor]

        outer_cell = None
        face = refs[2]
        cells_ptr = face.Cells_Cached(host_topology)
        for cell in cells_ptr:
            if not cell.IsSame(self):
                outer_cell = cell
        graph.add_edge(
            {
                start_coor: [
                    end_coor,
                    {
                        "start_vertex": refs[0],
                        "end_vertex": refs[1],
                        "face": refs[2],
                        "back_cell": self,
                        "front_cell": outer_cell,
                    },
                ]
            }
        )
    # FIXME should return list of cycles, with outer perimeter first (to support doughnut shaped rooms)
    return graph.find_paths()[0]


setattr(topologic_core.Cell, "FacesTop", FacesTop)
setattr(topologic_core.Cell, "FacesBottom", FacesBottom)
setattr(topologic_core.Cell, "FacesVerticalExternal", FacesVerticalExternal)
setattr(topologic_core.Cell, "CellsAbove", CellsAbove)
setattr(topologic_core.Cell, "CellsBelow", CellsBelow)
setattr(topologic_core.Cell, "Usage", Usage)
setattr(topologic_core.Cell, "IsOutside", IsOutside)
setattr(topologic_core.Cell, "PlanArea", PlanArea)
setattr(topologic_core.Cell, "ExternalWallArea", ExternalWallArea)
setattr(topologic_core.Cell, "Crinkliness", Crinkliness)
setattr(topologic_core.Cell, "Perimeter", Perimeter)
