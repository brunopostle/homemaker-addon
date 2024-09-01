"""Overloads domain-specific methods onto topologic.Edge"""

import topologic
from topologic import VertexUtility
from .helpers import el


def IsHorizontal(self):
    """Is this Edge horizontal?"""
    if el(self.StartVertex().Z()) == el(self.EndVertex().Z()):
        return True
    return False


def IsVertical(self):
    """Is this Edge vertical?"""
    if (
        abs(self.StartVertex().X() - self.EndVertex().X()) < 0.0001
        and abs(self.StartVertex().Y() - self.EndVertex().Y()) < 0.0001
    ):
        return True
    return False


# FIXME doesn't appear to be in use
def FaceAbove(self, host_topology):
    """Is there a vertical Face attached above? Returns None or a single Face"""
    faces_ptr = []
    self.Faces(host_topology, faces_ptr)
    for face in faces_ptr:
        if face.IsVertical() and face.Centroid().Z() > self.Centroid().Z():
            return face
    return None


def FacesBelow(self, host_topology):
    """Returns a list of non-horizontal Faces attached below this Edge"""
    faces_ptr = []
    faces_result = []
    self.Faces(host_topology, faces_ptr)
    for face in faces_ptr:
        if face.Centroid().Z() < self.Centroid().Z():
            faces_result.append(face)
    return faces_result


def CellsBelow(self, host_topology):
    """Returns a list of Cells attached below this Edge"""
    result_cells_ptr = []
    cells_ptr = self.Cells_Cached(host_topology)
    for cell in cells_ptr:
        if cell.Centroid().Z() < self.Centroid().Z():
            result_cells_ptr.append(cell)
    return result_cells_ptr


def Length(self):
    """Straight-line distance between start and end Vertex"""
    return VertexUtility.Distance(self.StartVertex(), self.EndVertex())


def NormalisedVector(self):
    """Vector with a magnitude of 1.0 parallel to this Edge"""
    start = self.StartVertex().Coordinates()
    end = self.EndVertex().Coordinates()
    length = self.Length()
    if length == 0.0:
        return [1.0, 0.0, 0.0]
    return [
        (end[0] - start[0]) / length,
        (end[1] - start[1]) / length,
        (end[2] - start[2]) / length,
    ]


setattr(topologic.Edge, "IsHorizontal", IsHorizontal)
setattr(topologic.Edge, "IsVertical", IsVertical)
setattr(topologic.Edge, "FaceAbove", FaceAbove)
setattr(topologic.Edge, "FacesBelow", FacesBelow)
setattr(topologic.Edge, "CellsBelow", CellsBelow)
setattr(topologic.Edge, "Length", Length)
setattr(topologic.Edge, "NormalisedVector", NormalisedVector)
