import topologic
from topologic import Face, Cluster, Cell, Topology, FaceUtility, CellUtility
from topologist.helpers import create_stl_list, el
from topologist import traces


def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Outside'"""
    if len(widgets) == 0:
        return
    cells = create_stl_list(Cell)
    self.Cells(cells)
    for cell in cells:
        cell.Set("usage", "outside")
        # a usable space has vertical faces on all sides
        if not cell.Perimeter().is_simple_cycle():
            cell.Set("usage", "void")
        for widget in widgets:
            if CellUtility.Contains(cell, widget[1]) == 0:
                cell.Set("usage", widget[0].lower())


def Roof(self):
    faces = create_stl_list(Face)
    self.Faces(faces)
    roof_faces = create_stl_list(Topology)
    for face in faces:
        if not face.IsVertical() and not face.IsHorizontal():
            cells = create_stl_list(Cell)
            face.Cells(cells)
            if len(list(cells)) == 1:
                roof_faces.push_back(face)
    # FIXME normals are not automatically unified facing up
    cluster = Cluster.ByTopologies(roof_faces)
    if len(list(roof_faces)) == 0:
        return None
    return cluster.SelfMerge()


# TODO non-horizontal details (gables, arches, ridges and valleys)


def GetTraces(self):
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""
    mytraces = traces.Traces()
    faces = create_stl_list(Face)
    self.Faces(faces)

    for face in faces:
        if face.IsVertical():
            elevation = face.Elevation()
            height = face.Height()
            style = face.Get("style")
            if not style:
                style = "default"

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                if face.IsOpen():
                    mytraces.add_axis("open", elevation, height, style, axis, face)

                elif face.IsExternal():
                    mytraces.add_axis("external", elevation, height, style, axis, face)

                elif face.IsInternal():
                    mytraces.add_axis_simple(
                        "internal", elevation, height, style, axis, face
                    )

                    # collect foundation strips
                    if not face.FaceBelow():
                        mytraces.add_axis_simple(
                            "internal-unsupported",
                            elevation,
                            0.0,
                            style,
                            axis,
                            face,
                        )

            if face.IsExternal():
                for condition in face.TopLevelConditions():
                    edge = condition[0]
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        el(elevation + height),
                        0.0,
                        style,
                        [edge.EndVertex(), edge.StartVertex()],
                        face,
                    )

                for condition in face.BottomLevelConditions():
                    edge = condition[0]
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        elevation,
                        0.0,
                        style,
                        [edge.StartVertex(), edge.EndVertex()],
                        face,
                    )

    cells = create_stl_list(Cell)
    self.Cells(cells)
    for cell in cells:
        perimeter = cell.Perimeter()
        if not perimeter.is_simple_cycle():
            continue
        elevation = cell.Elevation()
        height = cell.Height()
        style = "default"

        usage = cell.Usage()
        mytraces.add_trace(usage, elevation, height, style, perimeter)

    mytraces.process()
    return mytraces


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


def ApplyDictionary(self, source_faces):
    """Copy Dictionary items from a collection of faces"""
    faces = create_stl_list(Face)
    self.Faces(faces)
    for face in faces:
        vertex = FaceUtility.InternalVertex(face)
        for source_face in source_faces:
            if FaceUtility.IsInside(source_face, vertex, 0.001):
                dictionary = source_face.GetDictionary()
                for key in dictionary.Keys():
                    face.Set(key, source_face.Get(key))


setattr(topologic.CellComplex, "AllocateCells", AllocateCells)
setattr(topologic.CellComplex, "Roof", Roof)
setattr(topologic.CellComplex, "GetTraces", GetTraces)
setattr(topologic.CellComplex, "Elevations", Elevations)
setattr(topologic.CellComplex, "ApplyDictionary", ApplyDictionary)
