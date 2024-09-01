"""Overloads domain-specific methods onto topologic.Topology"""

from functools import lru_cache
import topologic
from topologic import StringAttribute, Vertex, FaceUtility
from .helpers import el
from . import traces
from . import hulls
from . import normals


@lru_cache(maxsize=256)
def Cells_Cached(self, host_topology):
    """List of Cells directly attached to this Topology"""
    cells_ptr = []
    self.Cells(host_topology, cells_ptr)
    return cells_ptr


@lru_cache(maxsize=256)
def Faces_Cached(self, host_topology):
    """List of Faces directly attached to this Topology"""
    faces_ptr = []
    self.Faces(host_topology, faces_ptr)
    return faces_ptr


def FacesVertical(self, faces_ptr):
    """List of vertical Faces within this Topology"""
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if face.IsVertical():
            faces_ptr.append(face)


# FIXME doesn't appear to be in use
def FacesHorizontal(self, faces_ptr):
    """List of horizontal Faces within this Topology"""
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if face.IsHorizontal():
            faces_ptr.append(face)


def FacesInclined(self, faces_ptr):
    """List of inclined Faces within this Topology"""
    if self.__class__ == Vertex:
        # Faces() is for searching sub-topologies and a Vertex has none
        return
    elements_ptr = []
    self.Faces(None, elements_ptr)
    for face in elements_ptr:
        if not face.IsHorizontal() and not face.IsVertical():
            faces_ptr.append(face)


def FacesWorld(self, host_topology):
    """List of external world Faces directly attached to this Topology"""
    faces_ptr = []
    elements_ptr = self.Faces_Cached(host_topology)
    for face in elements_ptr:
        if face.IsWorld(host_topology):
            faces_ptr.append(face)
    return faces_ptr


@lru_cache(maxsize=256)
def Elevation(self):
    """Lowest Z-height in this Topology"""
    lowest = 9999999.9
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for vertex in vertices_ptr:
        if vertex.Z() < lowest:
            lowest = vertex.Z()
    return el(lowest)


@lru_cache(maxsize=256)
def Height(self):
    """Vertical distance between the lowest and highest points in this Topology"""
    highest = -9999999.9
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for vertex in vertices_ptr:
        if vertex.Z() > highest:
            highest = vertex.Z()
    return el(highest - self.Elevation())


def Mesh(self):
    """Returns a list of Vertex coordinates, and a list of indexed Faces"""
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    vertices = [vertex.Coordinates() for vertex in vertices_ptr]

    faces_ptr = []
    self.Faces(None, faces_ptr)
    faces = []
    for face in faces_ptr:
        wire_vertices_ptr = []
        face.ExternalBoundary().Vertices(None, wire_vertices_ptr)
        faces.append([self.VertexId(vertex) for vertex in wire_vertices_ptr])
    return vertices, faces


def MeshSplit(self):
    """Returns a list of Vertex coordinates, and indexed faces split by style"""
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    vertices = [vertex.Coordinates() for vertex in vertices_ptr]

    faces_ptr = []
    self.Faces(None, faces_ptr)
    faces = {}
    for face in faces_ptr:
        stylename = face.Get("stylename")
        if not stylename:
            stylename = "default"
        wire_vertices_ptr = []
        face.ExternalBoundary().Vertices(None, wire_vertices_ptr)
        if stylename not in faces:
            faces[stylename] = []
        faces[stylename].append([self.VertexId(vertex) for vertex in wire_vertices_ptr])
    return vertices, faces


def Set(self, key, value):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(str(key)):
        dictionary.Remove(str(key))
    dictionary.Add(str(str(key)), StringAttribute(str(value)))
    self.SetDictionary(dictionary)


def Get(self, key):
    """Simple string value dictionary access"""
    dictionary = self.GetDictionary()
    if dictionary.ContainsKey(str(key)):
        value = dictionary.ValueAtKey(str(key))
        return str(value.StringValue())
    return None


def DumpDictionary(self):
    """Dump string attributes as a python dictionary"""
    dictionary = self.GetDictionary()
    keys = dictionary.Keys()
    result = {}
    for key in keys:
        value = self.Get(str(key))
        result[str(key)] = value
    return result


def GraphVertex(self, graph):
    """What Vertex in a given Graph corresponds with this Topology"""
    index = self.Get("index")
    myclass = type(self).__name__
    if index is not None:
        vertices_ptr = []
        graph.Vertices(vertices_ptr)
        for vertex in vertices_ptr:
            if vertex.Get("index") == index and vertex.Get("class") == myclass:
                return vertex


@lru_cache(maxsize=256)
def VertexId(self, vertex):
    i = 0
    vertices_ptr = []
    self.Vertices(None, vertices_ptr)
    for v in vertices_ptr:
        if v.IsSame(vertex):
            return i
        i += 1


def ApplyDictionary(self, source_faces_ptr):
    """Copy Dictionary items from a list of Faces onto this CellComplex"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        vertex = FaceUtility.InternalVertex(face, 0.001)
        normal = face.Normal()
        for source_face in source_faces_ptr:
            if abs(dot_product_3d(normal, source_face.Normal())) < 0.99:
                continue
            if not source_face.IsCoplanar(face):
                continue

            if FaceUtility.IsInside(source_face, vertex, 0.001):
                dictionary = source_face.GetDictionary()
                for key in dictionary.Keys():
                    face.Set(key, source_face.Get(key).split(".")[0])
                break


def dot_product_3d(A, B):
    return (A[0] * B[0]) + (A[1] * B[1]) + (A[2] * B[2])


def IndexTopology(self):
    """Index all faces starting at zero"""
    # TODO should retain existing index numbers
    faces_ptr = []
    self.Faces(None, faces_ptr)
    index = 0
    for face in faces_ptr:
        face.Set("index", str(index))
        face.Set("class", "Face")
        index += 1


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
        if not stylename:
            stylename = "default"
        if face.IsVertical():
            elevation = face.Elevation()
            height = face.Height()

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                mytraces.add_axis(
                    "external",
                    elevation,
                    height,
                    stylename,
                    start_vertex=axis[0],
                    end_vertex=axis[1],
                    face=face,
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

                elevations[elevation] = 0

                normal = face.Normal()
                for condition in face.TopLevelConditions(self):
                    edge = condition[0]
                    axis = [edge.EndVertex(), edge.StartVertex()]
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        el(elevation + height),
                        0.0,
                        stylename,
                        start_vertex=axis[0],
                        end_vertex=axis[1],
                        face=face,
                    )
                    elevations[el(elevation + height)] = 0

                for condition in face.BottomLevelConditions(self):
                    edge = condition[0]
                    axis = [edge.StartVertex(), edge.EndVertex()]
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        elevation,
                        0.0,
                        stylename,
                        start_vertex=axis[0],
                        end_vertex=axis[1],
                        face=face,
                    )

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

        if face.IsVertical():
            if face.AxisOuter():
                # these hulls are duplicates of traces with the same names
                myhulls.add_face(
                    "external",
                    stylename,
                    face=face,
                )
            else:
                # vertical face has no horizontal bottom edge, add to hull for wall panels
                myhulls.add_face(
                    "external-panel",
                    stylename,
                    face=face,
                )
        elif face.IsHorizontal():
            # collect flat roof areas (not outside spaces)
            if face.IsUpward():
                myhulls.add_face(
                    "flat",
                    stylename,
                    face=face,
                )
            else:
                myhulls.add_face(
                    "soffit",
                    stylename,
                    face=face,
                )
        else:
            # collect roof, soffit, and vaulted ceiling faces as hulls
            if face.IsUpward():
                myhulls.add_face(
                    "roof",
                    stylename,
                    face=face,
                )
            else:
                myhulls.add_face(
                    "soffit",
                    stylename,
                    face=face,
                )

    myhulls.process()
    return myhulls.hulls


setattr(topologic.Topology, "Cells_Cached", Cells_Cached)
setattr(topologic.Topology, "Faces_Cached", Faces_Cached)
setattr(topologic.Topology, "FacesVertical", FacesVertical)
setattr(topologic.Topology, "FacesHorizontal", FacesHorizontal)
setattr(topologic.Topology, "FacesInclined", FacesInclined)
setattr(topologic.Topology, "FacesWorld", FacesWorld)
setattr(topologic.Topology, "Elevation", Elevation)
setattr(topologic.Topology, "Height", Height)
setattr(topologic.Topology, "Mesh", Mesh)
setattr(topologic.Topology, "MeshSplit", MeshSplit)
setattr(topologic.Topology, "Set", Set)
setattr(topologic.Topology, "Get", Get)
setattr(topologic.Topology, "DumpDictionary", DumpDictionary)
setattr(topologic.Topology, "GraphVertex", GraphVertex)
setattr(topologic.Topology, "VertexId", VertexId)
setattr(topologic.Topology, "ApplyDictionary", ApplyDictionary)
setattr(topologic.Topology, "IndexTopology", IndexTopology)
setattr(topologic.Topology, "GetTraces", GetTraces)
setattr(topologic.Topology, "GetHulls", GetHulls)
