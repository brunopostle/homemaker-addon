import topologic
from topologic import Face, Cell, FaceUtility, CellUtility
from topologist.helpers import create_stl_list

def Volume(self):
    return CellUtility.Volume(self)

def FacesTop(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if(face.Elevation() == self.Elevation() + self.Height() and face.Height() == 0.0):
            faces_result.push_back(face)

def FacesBottom(self, faces_result):
    elements_ptr = create_stl_list(Face)
    self.Faces(elements_ptr)
    for face in elements_ptr:
        if(face.Elevation() == self.Elevation() and face.Height() == 0.0):
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

def IsOutside(self):
    """Cell with outdoor type"""
    # TODO
    return False

def PlanArea(self):
    # TODO
    pass

def ExternalWallArea(self):
    # TODO
    pass

def Crinkliness(self):
    if self.PlanArea() == 0.0:
        return 0.0
    return self.ExternalWallArea() / self.PlanArea()

def Perimeter(self):
    """2D outline of cell floor, closed, anti-clockwise"""
    # TODO
    pass

setattr(topologic.Cell, 'Volume', Volume)
setattr(topologic.Cell, 'FacesTop', FacesTop)
setattr(topologic.Cell, 'FacesBottom', FacesBottom)
setattr(topologic.Cell, 'CellsAbove', CellsAbove)
setattr(topologic.Cell, 'CellsBelow', CellsBelow)
setattr(topologic.Cell, 'IsOutside', IsOutside)
setattr(topologic.Cell, 'PlanArea', PlanArea)
setattr(topologic.Cell, 'ExternalWallArea', ExternalWallArea)
setattr(topologic.Cell, 'Crinkliness', Crinkliness)
setattr(topologic.Cell, 'Perimeter', Perimeter)
