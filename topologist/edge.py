import topologic
from topologic import Face, Cell
from topologist.helpers import create_stl_list, el

def IsHorizontal(self):
    if el(self.StartVertex().Z()) == el(self.EndVertex().Z()):
        return True
    return False

def IsVertical(self):
    if abs(self.StartVertex().X() - self.EndVertex().X()) < 0.0001 and abs(self.StartVertex().Y() - self.EndVertex().Y()) < 0.0001:
        return True
    return False

def FaceAbove(self):
    """Is there a vertical face attached above?"""
    faces = create_stl_list(Face)
    self.Faces(faces)
    for face in faces:
        if face.IsVertical() and face.Centroid().Z() > self.Centroid().Z():
            return face
    return None

def FaceBelow(self):
    """Is there a vertical face attached below?"""
    faces = create_stl_list(Face)
    self.Faces(faces)
    for face in faces:
        if face.IsVertical() and face.Centroid().Z() < self.Centroid().Z():
            return face
    return None

def CellsBelow(self):
    """Are there Cells below this edge?"""
    result = create_stl_list(Cell)
    cells = create_stl_list(Cell)
    self.Cells(cells)
    for cell in cells:
        if cell.Centroid().Z() < self.Centroid().Z():
            result.push_back(cell)
    return result

setattr(topologic.Edge, 'IsHorizontal', IsHorizontal)
setattr(topologic.Edge, 'IsVertical', IsVertical)
setattr(topologic.Edge, 'FaceAbove', FaceAbove)
setattr(topologic.Edge, 'FaceBelow', FaceBelow)
setattr(topologic.Edge, 'CellsBelow', CellsBelow)
