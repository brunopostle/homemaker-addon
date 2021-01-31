import topologic
from topologic import Face, CellComplex
from topologist.helpers import create_stl_list

def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Living'"""
    # TODO
    pass

def PruneGraph(self):
    """Reduce circulation graph"""
    # TODO
    pass

def FacesVerticalInternal(self, faces_result):
    # TODO
    pass

def FacesVerticalExternal(self, faces_result):
    # TODO
    pass

def FacesVerticalWorld(self, faces_result):
    # TODO
    pass

def FacesVerticalOpen(self, faces_result):
    # TODO
    pass

def FacesHorizontalInternal(self, faces_result):
    # TODO
    pass

def FacesHorizontalExternal(self, faces_result):
    # TODO
    pass

def WallsExternal(self):
    """Construct a graph of external vertical faces for each elevation and height"""
    # TODO
    pass

def WallsExternalUnsupported(self):
    """Construct a graph of unsupported external vertical faces for each elevation"""
    # TODO
    pass

def WallsEaves(self):
    """Construct a graph of external vertical faces with no solid wall above for each elevation"""
    # TODO
    pass

def WallsOpen(self):
    """"Construct a graph of open vertical faces"""
    # TODO
    pass

def WallsInternal(self):
    """"Construct a graph of internal vertical faces for each elevation and height"""
    # TODO
    pass

def WallsInternalUnsupported(self):
    """Construct a graph of unsupported internal vertical faces for each elevation"""
    # TODO
    pass

def Elevations(self):
    """Identify all unique elevations, allocate level index"""
    # TODO
    pass

setattr(topologic.CellComplex, 'AllocateCells', AllocateCells)
setattr(topologic.CellComplex, 'PruneGraph', PruneGraph)
setattr(topologic.CellComplex, 'FacesVerticalInternal', FacesVerticalInternal)
setattr(topologic.CellComplex, 'FacesVerticalExternal', FacesVerticalExternal)
setattr(topologic.CellComplex, 'FacesVerticalWorld', FacesVerticalWorld)
setattr(topologic.CellComplex, 'FacesVerticalOpen', FacesVerticalOpen)
setattr(topologic.CellComplex, 'FacesHorizontalInternal', FacesHorizontalInternal)
setattr(topologic.CellComplex, 'FacesHorizontalExternal', FacesHorizontalExternal)
setattr(topologic.CellComplex, 'WallsExternal', WallsExternal)
setattr(topologic.CellComplex, 'WallsExternalUnsupported', WallsExternalUnsupported)
setattr(topologic.CellComplex, 'WallsEaves', WallsEaves)
setattr(topologic.CellComplex, 'WallsOpen', WallsOpen)
setattr(topologic.CellComplex, 'WallsInternal', WallsInternal)
setattr(topologic.CellComplex, 'WallsInternalUnsupported', WallsInternalUnsupported)
setattr(topologic.CellComplex, 'Elevations', Elevations)
