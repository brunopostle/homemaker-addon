import topologic
from topologic import Face, Cluster, Cell, Topology, FaceUtility, CellUtility
from topologist.helpers import create_stl_list, vertex_string, el
from topologist import ugraph


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


def Traces(self):
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""
    traces = {
        "external": {},
        "open": {},
        "top-vertical-up": {},
        "top-backward-level": {},
        "top-backward-up": {},
        "top-backward-down": {},
        "top-forward-level": {},
        "top-forward-up": {},
        "top-forward-down": {},
        "bottom-vertical-down": {},
        "bottom-backward-level": {},
        "bottom-backward-up": {},
        "bottom-backward-down": {},
        "bottom-forward-level": {},
        "bottom-forward-up": {},
        "bottom-forward-down": {},
        "internal": {},
        "internal-unsupported": {},
    }
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
                    add_axis(traces["open"], elevation, height, style, axis, face)

                elif face.IsExternal():
                    add_axis(traces["external"], elevation, height, style, axis, face)

                elif face.IsInternal():
                    add_axis_simple(
                        traces["internal"], elevation, height, style, axis, face
                    )

                    # collect foundation strips
                    if not face.FaceBelow():
                        add_axis_simple(
                            traces["internal-unsupported"],
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
                    add_axis(
                        traces[label],
                        el(elevation + height),
                        0.0,
                        style,
                        [edge.EndVertex(), edge.StartVertex()],
                        face,
                    )

                for condition in face.BottomLevelConditions():
                    edge = condition[0]
                    label = condition[1]
                    add_axis(
                        traces[label],
                        el(elevation),
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
        if not usage in traces:
            traces[usage] = {}
        if not elevation in traces[usage]:
            traces[usage][elevation] = {}
        if not height in traces[usage][elevation]:
            traces[usage][elevation][height] = {}
        if not style in traces[usage][elevation][height]:
            traces[usage][elevation][height][style] = []
        traces[usage][elevation][height][style].append(perimeter)

    for usage in traces:
        for elevation in traces[usage]:
            for height in traces[usage][elevation]:
                for style in traces[usage][elevation][height]:
                    if traces[usage][elevation][height][style].__class__ == [].__class__:
                        continue
                    graphs = traces[usage][elevation][height][style].find_paths()
                    traces[usage][elevation][height][style] = graphs

    return traces


def add_axis(trace_type, elevation, height, style, edge, face):
    """helper function to isolate graph library related code"""
    if not elevation in trace_type:
        trace_type[elevation] = {}
    if not height in trace_type[elevation]:
        trace_type[elevation][height] = {}
    if not style in trace_type[elevation][height]:
        trace_type[elevation][height][style] = ugraph.graph()

    start_coor = vertex_string(edge[0])
    end_coor = vertex_string(edge[1])
    trace_type[elevation][height][style].add_edge(
        {start_coor: [end_coor, [edge[0], edge[1], face]]}
    )


def add_axis_simple(trace_type, elevation, height, style, edge, face):
    """helper function for traces that don't form chains or loops"""
    if not elevation in trace_type:
        trace_type[elevation] = {}
    if not height in trace_type[elevation]:
        trace_type[elevation][height] = {}
    if not style in trace_type[elevation][height]:
        trace_type[elevation][height][style] = []

    start_coor = vertex_string(edge[0])
    end_coor = vertex_string(edge[1])
    graph = ugraph.graph()
    graph.add_edge({start_coor: [end_coor, [edge[0], edge[1], face]]})
    trace_type[elevation][height][style].append(graph)


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
setattr(topologic.CellComplex, "Traces", Traces)
setattr(topologic.CellComplex, "Elevations", Elevations)
setattr(topologic.CellComplex, "ApplyDictionary", ApplyDictionary)
