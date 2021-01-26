import cppyy
import topologic
from topologic import Cell, CellUtility

def Volume(self):
    return CellUtility.Volume(self)

setattr(topologic.Cell, 'Volume', Volume)
