"""Overloads domain-specific methods onto topologic_core.CellComplex"""

import topologic_core
from topologic_core import Graph, CellUtility
from .helpers import el
from . import traces
from . import hulls
from . import normals


def IndexTopology(self):
    """Index all cells and faces starting at zero"""
    # TODO should retain existing index numbers
    cells_ptr = []
    self.Cells(None, cells_ptr)
    index = 0
    for cell in cells_ptr:
        cell.Set("index", str(index))
        cell.Set("class", "Cell")
        index += 1

    faces_ptr = []
    self.Faces(None, faces_ptr)
    index = 0
    for face in faces_ptr:
        face.Set("index", str(index))
        face.Set("class", "Face")
        index += 1


def AllocateCells(self, widgets):
    """Set Cell types using a list of widgets, or default to 'living' ('void' when no Perimeter).
    A widget is any topology (typically a Vertex) with 'usage' tagged"""
    cells_ptr = []
    self.Cells(None, cells_ptr)
    for cell in cells_ptr:
        cell.Set("usage", "living")
        # a usable space has vertical faces on all sides
        if not cell.Perimeter(self).is_simple_cycle():
            cell.Set("usage", "void")
            continue
        for widget in widgets:
            if CellUtility.Contains(cell, widget, 0.001) == 0:
                cell.Set("usage", widget.Get("usage").lower())
                break

    # tag faces between inside and outside spaces that face inwards
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        face.BadNormal(self)


def Adjacency(self):
    """Returns a Topologic adjacency Graph that has nodes for Cells, and nodes for Faces that connect them"""
    # a graph where each cell and face between them has a vertex
    return Graph.ByTopology(self, False, True, False, False, False, False, 0.0001)


# TODO non-horizontal details (gables, arches, ridges and valleys)


def GetTraces(self):
    """Returns 'traces', 'normals' and 'elevations' dictionaries.
    Traces are 2D ugraph paths that define walls, extrusions and rooms.
    Normals indicate horizontal mitre direction for corners.
    Elevations indicate a 'level' id for each height in the model."""
    mytraces = traces.Traces()
    mynormals = normals.Normals()
    elevations = {}

    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        stylename = face.Get("stylename")
        front_cell, back_cell = face.CellsOrdered(self)
        if not stylename:
            stylename = "default"
        if face.IsVertical():
            elevation = face.Elevation()
            height = face.Height()

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                if face.IsOpen(self):
                    mytraces.add_axis(
                        "open",
                        elevation,
                        height,
                        stylename,
                        start_vertex=axis[0],
                        end_vertex=axis[1],
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )

                elif face.IsExternal(self):
                    mytraces.add_axis(
                        "external",
                        elevation,
                        height,
                        stylename,
                        start_vertex=axis[0],
                        end_vertex=axis[1],
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
                    # build normal map
                    normal = face.Normal()
                    edges_ptr = []
                    face.EdgesTop(edges_ptr)
                    for edge in edges_ptr:
                        axis = [edge.EndVertex(), edge.StartVertex()]
                        if face.Get("badnormal"):
                            axis.reverse()
                        mynormals.add_vector("top", axis[0], normal)
                        mynormals.add_vector("top", axis[1], normal)
                    edges_ptr = []
                    face.EdgesBottom(edges_ptr)
                    for edge in edges_ptr:
                        axis = [edge.StartVertex(), edge.EndVertex()]
                        if face.Get("badnormal"):
                            axis.reverse()
                        mynormals.add_vector("bottom", axis[0], normal)
                        mynormals.add_vector("bottom", axis[1], normal)

                elif face.IsInternal(self):
                    mytraces.add_axis_simple(
                        "internal",
                        elevation,
                        height,
                        stylename,
                        start_vertex=axis[0],
                        end_vertex=axis[1],
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )

                    # collect foundation strips
                    if not face.FacesBelow(self):
                        if not face.CellsBelow(self):
                            mytraces.add_axis_simple(
                                "internal-footing",
                                elevation,
                                0.0,
                                stylename,
                                start_vertex=axis[0],
                                end_vertex=axis[1],
                                face=face,
                                front_cell=front_cell,
                                back_cell=back_cell,
                            )
                        else:
                            mytraces.add_axis_simple(
                                "internal-beam",
                                elevation,
                                0.0,
                                stylename,
                                start_vertex=axis[0],
                                end_vertex=axis[1],
                                face=face,
                                front_cell=front_cell,
                                back_cell=back_cell,
                            )
                elevations[elevation] = 0

                if face.IsWorld(self):
                    normal = face.Normal()
                    for condition in face.TopLevelConditions(self):
                        edge = condition[0]
                        axis = [edge.EndVertex(), edge.StartVertex()]
                        if face.Get("badnormal"):
                            axis.reverse()
                        label = condition[1]
                        mytraces.add_axis(
                            label,
                            el(elevation + height),
                            0.0,
                            stylename,
                            start_vertex=axis[0],
                            end_vertex=axis[1],
                            face=face,
                            front_cell=front_cell,
                            back_cell=back_cell,
                        )
                        elevations[el(elevation + height)] = 0

                    for condition in face.BottomLevelConditions(self):
                        edge = condition[0]
                        axis = [edge.StartVertex(), edge.EndVertex()]
                        if face.Get("badnormal"):
                            axis.reverse()
                        label = condition[1]
                        mytraces.add_axis(
                            label,
                            elevation,
                            0.0,
                            stylename,
                            start_vertex=axis[0],
                            end_vertex=axis[1],
                            face=face,
                            front_cell=front_cell,
                            back_cell=back_cell,
                        )

    cells_ptr = []
    self.Cells(None, cells_ptr)
    for cell in cells_ptr:
        perimeter = cell.Perimeter(self)
        if perimeter.is_simple_cycle():
            elevation = cell.Elevation()
            height = cell.Height()
            faces_bottom = []
            cell.FacesBottom(faces_bottom)
            stylename = faces_bottom[0].Get("stylename")
            if not stylename:
                stylename = "default"

            usage = cell.Usage()
            mytraces.add_trace(usage, elevation, height, stylename, graph=perimeter)
            elevations[elevation] = 0

    mytraces.process()
    mynormals.process()
    level = 0
    keys = list(elevations.keys())
    keys.sort()
    for elevation in keys:
        elevations[elevation] = level
        level += 1
    return (mytraces.traces, mynormals.normals, elevations)


def GetHulls(self):
    """Returns a 'hulls' dictionary. Hulls are 3D ushell surfaces that define roofs, soffits etc.."""
    myhulls = hulls.Hulls()

    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        stylename = face.Get("stylename")
        if not stylename:
            stylename = "default"
        front_cell, back_cell = face.CellsOrdered(self)

        if face.IsVertical():
            if face.AxisOuter():
                # these hulls are duplicates of traces with the same names
                if face.IsOpen(self):
                    myhulls.add_face(
                        "open",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
                elif face.IsExternal(self):
                    myhulls.add_face(
                        "external",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
                elif face.IsInternal(self):
                    myhulls.add_face(
                        "internal",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
            else:
                # vertical face has no horizontal bottom edge, add to hull for wall panels
                if face.IsExternal(self):
                    myhulls.add_face(
                        "external-panel",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
                else:
                    myhulls.add_face(
                        "internal-panel",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
        elif face.IsHorizontal():
            cell_above = face.CellAbove(self)
            # collect flat roof areas (not outside spaces)
            if face.IsUpward() and face.IsWorld(self):
                myhulls.add_face(
                    "flat",
                    stylename,
                    face=face,
                    front_cell=front_cell,
                    back_cell=back_cell,
                )
            elif cell_above:
                if cell_above.Usage() == "void":
                    if face.IsExternal(self):
                        myhulls.add_face(
                            "soffit",
                            stylename,
                            face=face,
                            front_cell=front_cell,
                            back_cell=back_cell,
                        )
                    else:
                        myhulls.add_face(
                            "vault",
                            stylename,
                            face=face,
                            front_cell=front_cell,
                            back_cell=back_cell,
                        )
                elif cell_above.Usage() is not None:
                    # these hulls are duplicates of traces with the same names
                    myhulls.add_face(
                        cell_above.Usage(),
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
        else:
            # collect roof, soffit, and vaulted ceiling faces as hulls
            if face.IsExternal(self):
                if face.IsUpward():
                    myhulls.add_face(
                        "roof",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
                else:
                    myhulls.add_face(
                        "soffit",
                        stylename,
                        face=face,
                        front_cell=front_cell,
                        back_cell=back_cell,
                    )
            else:
                myhulls.add_face(
                    "vault",
                    stylename,
                    face=face,
                    front_cell=front_cell,
                    back_cell=back_cell,
                )

    myhulls.process()
    return myhulls.hulls


def FootPrint(self):
    """returns the outline(s) of the cellcomplex at the lowest level"""
    try:
        cell = self.ExternalBoundary()
    except RuntimeError:
        cells_ptr = []
        self.Cells(None, cells_ptr)
        cell = cells_ptr[0]
    ugraph = cell.Perimeter(self)
    return ugraph.find_paths()


setattr(topologic_core.CellComplex, "IndexTopology", IndexTopology)
setattr(topologic_core.CellComplex, "AllocateCells", AllocateCells)
setattr(topologic_core.CellComplex, "Adjacency", Adjacency)
setattr(topologic_core.CellComplex, "GetTraces", GetTraces)
setattr(topologic_core.CellComplex, "GetHulls", GetHulls)
setattr(topologic_core.CellComplex, "FootPrint", FootPrint)
