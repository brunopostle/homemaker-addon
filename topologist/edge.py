"""Overloads domain-specific methods onto topologic.Edge"""

import topologic
from topologic import VertexUtility
from topologist.helpers import el


def IsHorizontal(self):
    if el(self.StartVertex().Z()) == el(self.EndVertex().Z()):
        return True
    return False


def IsVertical(self):
    if (
        abs(self.StartVertex().X() - self.EndVertex().X()) < 0.0001
        and abs(self.StartVertex().Y() - self.EndVertex().Y()) < 0.0001
    ):
        return True
    return False


# FIXME doesn't appear to be in use
def FaceAbove(self, host_topology):
    """Is there a vertical face attached above?"""
    faces_ptr = []
    self.Faces(host_topology, faces_ptr)
    for face in faces_ptr:
        if face.IsVertical() and face.Centroid().Z() > self.Centroid().Z():
            return face
    return None


def FacesBelow(self, host_topology):
    """Is there a non-horizontal face attached below?"""
    faces_ptr = []
    faces_result = []
    self.Faces(host_topology, faces_ptr)
    for face in faces_ptr:
        if face.Centroid().Z() < self.Centroid().Z():
            faces_result.append(face)
    return faces_result


def CellsBelow(self, host_topology):
    """Are there Cells below this edge?"""
    result_cells_ptr = []
    cells_ptr = self.Cells_Cached(host_topology)
    for cell in cells_ptr:
        if cell.Centroid().Z() < self.Centroid().Z():
            result_cells_ptr.append(cell)
    return result_cells_ptr


def Length(self):
    """Straight-line distance between start and end vertex"""
    return VertexUtility.Distance(self.StartVertex(), self.EndVertex())


setattr(topologic.Edge, "IsHorizontal", IsHorizontal)
setattr(topologic.Edge, "IsVertical", IsVertical)
setattr(topologic.Edge, "FaceAbove", FaceAbove)
setattr(topologic.Edge, "FacesBelow", FacesBelow)
setattr(topologic.Edge, "CellsBelow", CellsBelow)
setattr(topologic.Edge, "Length", Length)
