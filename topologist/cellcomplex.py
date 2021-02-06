import topologic
import networkx
from topologic import Face
from topologist.helpers import create_stl_list, vertex_string

def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Living'"""
    # TODO
    pass

def PruneGraph(self):
    """Reduce circulation graph"""
    # TODO
    pass

def Walls(self):
    """Construct a graph of external vertical faces for each elevation and height"""
    walls = {'external': {},
             'external_unsupported': {},
             'eaves': {},
             'open': {},
             'internal': {},
             'internal_unsupported': {}}
    faces = create_stl_list(Face)
    self.Faces(faces)

    for face in faces:
        if face.IsVertical():
            if face.IsExternal():
                edge = face.AxisOuter()
                if not edge: continue
                elevation = face.Elevation()
                height = face.Height()
                if not elevation in walls['external']:
                    walls['external'][elevation] = {}
                if not height in walls['external'][elevation]:
                    walls['external'][elevation][height] = networkx.DiGraph()

                start_coor = vertex_string(edge.StartVertex())
                end_coor = vertex_string(edge.EndVertex())
                walls['external'][elevation][height].add_edge(start_coor, end_coor, face=face)

    return walls

def Elevations(self):
    """Identify all unique elevations, allocate level index"""
    elevations = {}

    faces = create_stl_list(Face)
    self.Faces(faces)
    for face in faces:
        elevation = face.Elevation()
        elevations[float(elevation)] = 0

    level = 0
    keys = list(elevations.keys())
    keys.sort()
    for elevation in keys:
        elevations[elevation] = level
        level += 1
    return elevations

setattr(topologic.CellComplex, 'AllocateCells', AllocateCells)
setattr(topologic.CellComplex, 'PruneGraph', PruneGraph)
setattr(topologic.CellComplex, 'Walls', Walls)
setattr(topologic.CellComplex, 'Elevations', Elevations)
