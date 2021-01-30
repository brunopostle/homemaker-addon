import topologic
from topologic import Face, Cell, CellUtility
from topologist.helpers import create_stl_list

def Volume(self):
    return CellUtility.Volume(self)

def FacesTop(self):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if(face.Elevation() == self.Elevation() + self.Height() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

def FacesBottom(self):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    faces_result = []
    for face in elements_ptr:
        if(face.Elevation() == self.Elevation() and face.Height() == 0.0):
            faces_result.append(face)
    return faces_result

def CellsAbove(self):
    """Cells (excluding self) connected to top faces of this cell"""
    faces_top = self.FacesTop()
    elements_ptr = create_stl_list(Cell)
    self.Cells(elements_ptr)
    cells_result = []
    for cell in elements_ptr:
        if not cell is self:
            if cell in faces_top:
                cells_result.append(cell)
    return cells_result

def CellsBelow(self):
    """Cells (excluding self) connected to bottom faces of this cell"""
    faces_bottom = self.FacesBottom()
    elements_ptr = create_stl_list(Cell)
    self.Cells(elements_ptr)
    cells_result = []
    for cell in elements_ptr:
        if not cell is self:
            if cell in faces_bottom:
                cells_result.append(cell)
    return cells_result

def IsOutside(self):
    """Cell with outdoor type"""
    # FIXME
    return False

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
setattr(topologic.Cell, 'CellsAbove', CellsAbove)
setattr(topologic.Cell, 'CellsBelow', CellsBelow)
setattr(topologic.Cell, 'IsOutside', IsOutside)
