"""Overloads domain-specific methods onto topologic.CellComplex"""

import topologic
from topologic import FaceUtility, CellUtility
from topologist.helpers import el
import topologist.traces
import topologist.hulls
import topologist.normals


def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Outside'"""
    if len(widgets) == 0:
        return
    cells_ptr = []
    self.Cells(cells_ptr)
    for cell in cells_ptr:
        cell.Set("usage", "living")
        # a usable space has vertical faces on all sides
        if not cell.Perimeter().is_simple_cycle():
            cell.Set("usage", "void")
            continue
        for widget in widgets:
            if CellUtility.Contains(cell, widget[1], 0.001) == 0:
                cell.Set("usage", widget[0].lower())
                break


# TODO non-horizontal details (gables, arches, ridges and valleys)


def GetTraces(self):
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""
    mytraces = topologist.traces.Traces()
    myhulls = topologist.hulls.Hulls()
    mynormals = topologist.normals.Normals()
    elevations = {}
    faces_ptr = []
    self.Faces(faces_ptr)

    for face in faces_ptr:
        # labelling "badnormal" faces should be a separate method but here is convenient for now
        face.BadNormal()
    for face in faces_ptr:
        stylename = face.Get("stylename")
        if not stylename:
            stylename = "default"
        if face.IsVertical():
            elevation = face.Elevation()
            height = face.Height()

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                if face.IsOpen():
                    mytraces.add_axis("open", elevation, height, stylename, axis, face)

                elif face.IsExternal():
                    mytraces.add_axis(
                        "external", elevation, height, stylename, axis, face
                    )

                elif face.IsInternal():
                    mytraces.add_axis_simple(
                        "internal", elevation, height, stylename, axis, face
                    )

                    # collect foundation strips
                    if not face.FaceBelow():
                        mytraces.add_axis_simple(
                            "internal-unsupported",
                            elevation,
                            0.0,
                            stylename,
                            axis,
                            face,
                        )
                elevations[elevation] = 0
            else:
                # face has no horizontal bottom edge, add to hull for wall panels
                myhulls.add_face("panel", stylename, face)

            # TODO open wall top and bottom traces
            if face.IsExternal():
                normal = face.Normal()
                for condition in face.TopLevelConditions():
                    edge = condition[0]
                    vertices = [edge.EndVertex(), edge.StartVertex()]
                    if face.Get("badnormal"):
                        vertices.reverse()
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        el(elevation + height),
                        0.0,
                        stylename,
                        vertices,
                        face,
                    )
                    mynormals.add_vector("top", edge.StartVertex(), normal)
                    mynormals.add_vector("top", edge.EndVertex(), normal)
                    elevations[el(elevation + height)] = 0

                for condition in face.BottomLevelConditions():
                    edge = condition[0]
                    vertices = [edge.StartVertex(), edge.EndVertex()]
                    if face.Get("badnormal"):
                        vertices.reverse()
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        elevation,
                        0.0,
                        stylename,
                        vertices,
                        face,
                    )
                    mynormals.add_vector("bottom", edge.StartVertex(), normal)
                    mynormals.add_vector("bottom", edge.EndVertex(), normal)

        elif face.IsHorizontal():
            # collect flat roof areas (not outdoor spaces)
            if face.IsUpward() and face.IsWorld():
                myhulls.add_face("flat", stylename, face)
        else:
            # collect roof, soffit, and vaulted ceiling faces as hulls
            if face.IsUpward():
                myhulls.add_face("roof", stylename, face)
            else:
                myhulls.add_face("soffit", stylename, face)

    cells_ptr = []
    self.Cells(cells_ptr)
    for cell in cells_ptr:
        perimeter = cell.Perimeter()
        if perimeter.is_simple_cycle():
            elevation = cell.Elevation()
            height = cell.Height()
            stylename = "default"

            usage = cell.Usage()
            mytraces.add_trace(usage, elevation, height, stylename, perimeter)
            elevations[elevation] = 0

    mytraces.process()
    myhulls.process()
    mynormals.process()
    level = 0
    keys = list(elevations.keys())
    keys.sort()
    for elevation in keys:
        elevations[elevation] = level
        level += 1
    return (mytraces.traces, myhulls.hulls, mynormals.normals, elevations)


def ApplyDictionary(self, source_faces_ptr):
    """Copy Dictionary items from a collection of faces"""
    faces_ptr = []
    self.Faces(faces_ptr)
    for face in faces_ptr:
        vertex = FaceUtility.InternalVertex(face, 0.001)
        for source_face in source_faces_ptr:
            # FIXME calling IsInside() many times slows subsequent code!!
            if FaceUtility.IsInside(source_face, vertex, 0.001):
                dictionary = source_face.GetDictionary()
                for key in dictionary.Keys():
                    face.Set(key, source_face.Get(key).split(".")[0])
                break


setattr(topologic.CellComplex, "AllocateCells", AllocateCells)
setattr(topologic.CellComplex, "GetTraces", GetTraces)
setattr(topologic.CellComplex, "ApplyDictionary", ApplyDictionary)
