import topologic
from topologic import Face, Cluster, Cell
from topologist.helpers import create_stl_list, vertex_string
from topologist import ugraph

def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Living'"""
    # TODO
    pass

def PruneGraph(self):
    """Reduce circulation graph"""
    # TODO
    pass

def Roof(self):
    faces = create_stl_list(Face)
    self.Faces(faces)
    roof_faces = create_stl_list(Face)
    for face in faces:
        if not face.IsVertical() and not face.IsHorizontal():
            cells = create_stl_list(Cell)
            face.Cells(cells)
            if len(list(cells)) == 1:
                roof_faces.push_back(face)
    return Cluster.ByFaces(roof_faces)

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
            elevation = face.Elevation()
            height = face.Height()

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                if face.IsOpen():
                    add_axis(walls['open'], elevation, height, axis, face)

                if face.IsExternal():
                    add_axis(walls['external'], elevation, height, axis, face)

                    # collect foundation strips
                    if not face.FaceBelow():
                        add_axis(walls['external_unsupported'], elevation, 0.0, axis, face)

                if face.IsInternal():
                    add_axis_simple(walls['internal'], elevation, height, axis, face)

                    # collect foundation strips
                    if not face.FaceBelow():
                        add_axis_simple(walls['internal_unsupported'], elevation, 0.0, axis, face)

            axis_top = face.AxisOuterTop()
            # wall face may be triangular and not have a top edge
            if axis_top:
                if face.IsWorld():

                    # collect eaves line
                    face_above = face.FaceAbove()
                    # either there is nothing above or it is an open space
                    if not (face_above and not face_above.IsOpen()):
                        add_axis(walls['eaves'], elevation + height, 0.0, axis_top, face)

    return walls

def add_axis(wall_type, elevation, height, edge, face):
   """helper function to isolate graph library related code"""
   if not elevation in wall_type:
       wall_type[elevation] = {}
   if not height in wall_type[elevation]:
       wall_type[elevation][height] = ugraph.graph()

   start_coor = vertex_string(edge.StartVertex())
   end_coor = vertex_string(edge.EndVertex())
   wall_type[elevation][height].add_edge({start_coor: [end_coor, face]})

def add_axis_simple(wall_type, elevation, height, edge, face):
   """helper function for walls that don't form chains or loops"""
   if not elevation in wall_type:
       wall_type[elevation] = {}
   if not height in wall_type[elevation]:
       wall_type[elevation][height] = []

   start_coor = vertex_string(edge.StartVertex())
   end_coor = vertex_string(edge.EndVertex())
   wall_type[elevation][height].append([start_coor, end_coor, face])

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
setattr(topologic.CellComplex, 'Roof', Roof)
setattr(topologic.CellComplex, 'Walls', Walls)
setattr(topologic.CellComplex, 'Elevations', Elevations)
