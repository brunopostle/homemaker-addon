"""Overloads domain-specific methods onto topologic.Graph"""

import topologic
from topologic import VertexUtility


def Circulation(self, cellcomplex):
    """Reduce an adjacency Graph to a circulation Graph.
    Uses heuristics for connecting rooms and floors between stair cells"""
    vertices_ptr = []
    for face in self.Faces(cellcomplex):
        vertex = face.GraphVertex(self)
        if face.IsVertical():
            # wall
            axis = face.AxisOuter()
            if axis == None or VertexUtility.Distance(axis[0], axis[1]) < 1.0:
                # is too narrow for a door
                vertices_ptr.append(vertex)
            else:
                cells_ptr = face.Cells_Cached(cellcomplex)
                cells = cells_ptr
                if cells[0].Elevation() != cells[1].Elevation():
                    # floors either side are not at the same level
                    vertices_ptr.append(vertex)
                else:
                    # TODO should use 'separation' attribute to prune excess doors
                    # TODO not between toilet and toilet or bedroom and bedroom
                    # FIXME this puts doors into 'void' spaces
                    usage_a = cells[0].Usage()
                    usage_b = cells[1].Usage()
                    if (usage_a == "bedroom" or usage_a == "toilet") and not (
                        usage_b == "stair" or usage_b == "circulation"
                    ):
                        vertices_ptr.append(vertex)
                    elif (usage_b == "bedroom" or usage_b == "toilet") and not (
                        usage_a == "stair" or usage_a == "circulation"
                    ):
                        vertices_ptr.append(vertex)

        elif face.IsHorizontal():
            # floor
            cells_ptr = face.Cells_Cached(cellcomplex)
            if (
                len(cells_ptr) == 2
                and cells_ptr[0].Usage() == "stair"
                and cells_ptr[1].Usage() == "stair"
            ):
                continue
            # is not in a stair flight
            vertices_ptr.append(vertex)
        else:
            # neither vertical or horizontal
            vertices_ptr.append(vertex)
    self.RemoveVertices(vertices_ptr)


def IsConnected(self):
    """Checks that all Vertices can be reached from all other Vertices"""
    connected = True
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    if vertices_ptr:
        vertex_a = vertices_ptr[0]
        for vertex_b in vertices_ptr:
            if vertex_b.Get("class") == "Face":
                continue
            if vertex_a.IsSame(vertex_b):
                continue
            distance = self.TopologicalDistance(vertex_a, vertex_b)
            if distance > 255:
                connected = False
    return connected


def ShortestPathTable(self):
    """Calculates shortest path distance between all pairs of cells and returns a lookup table"""
    result = {}
    if self.IsConnected():
        vertices_ptr = []
        self.Vertices(vertices_ptr)
        vertices_list = []
        for vertex in vertices_ptr:
            if vertex.Get("class") == "Cell":
                vertices_list.append(vertex)
        for i in range(len(vertices_list)):
            for j in range(len(vertices_list)):
                if j <= i:
                    continue
                wire = self.ShortestPath(
                    vertices_list[i], vertices_list[j], "", "length"
                )
                edges_ptr = []
                wire.Edges(None, edges_ptr)
                length = 0.0
                for edge in edges_ptr:
                    length += edge.Length()
                i_index = vertices_list[i].Get("index")
                j_index = vertices_list[j].Get("index")
                if not i_index in result:
                    result[i_index] = {}
                if not j_index in result:
                    result[j_index] = {}
                result[i_index][j_index] = length
                result[j_index][i_index] = length
    return result


def Separation(self, table, cellcomplex):
    """Tags 'cell' vertices with average travel distance to all other cells"""
    if table:
        vertices_ptr = []
        self.Vertices(vertices_ptr)
        for vertex in vertices_ptr:
            if vertex.Get("class") == "Cell":
                index = vertex.Get("index")
                total_length = 0.0
                for length in table[index].values():
                    total_length += length
                separation = str(total_length / len(table[index]))
                vertex.Set("separation", separation)
                self.GetEntity(cellcomplex, vertex).Set("separation", separation)


def Faces(self, cellcomplex):
    """Return all the Faces from a CellComplex corresponding to this Graph"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    faces_ptr = []
    for vertex in vertices_ptr:
        if vertex.Get("class") == "Face":
            face = self.GetEntity(cellcomplex, vertex)
            faces_ptr.append(face)
    return faces_ptr


def Cells(self, cellcomplex):
    """Return all the Cells from a CellComplex corresponding to this Graph"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    cells_ptr = []
    for vertex in vertices_ptr:
        if vertex.Get("class") == "Cell":
            cell = self.GetEntity(cellcomplex, vertex)
            cells_ptr.append(cell)
    return cells_ptr


def GetEntity(self, cellcomplex, vertex):
    """Return the entity from a CellComplex (Face or Cell) corresponding to this Vertex)"""
    index = vertex.Get("index")
    if vertex.Get("class") == "Face":
        topologies_ptr = []
        cellcomplex.Faces(None, topologies_ptr)
    elif vertex.Get("class") == "Cell":
        topologies_ptr = []
        cellcomplex.Cells(None, topologies_ptr)
    else:
        return None
    for entity in topologies_ptr:
        if entity.Get("index") == index:
            return entity


# FIXME doesn't appear to be in use
def Dot(self, cellcomplex):
    """A generic GraphViz .dot file"""
    # neato -Tpng < graph.dot > graph.png
    string = "strict graph G {\n"
    string += "graph [overlap=false];\n"

    vertices_ptr = []
    self.Vertices(vertices_ptr)

    edges_ptr = []
    self.Edges(edges_ptr)

    for vertex in vertices_ptr:
        text = str(self.GetEntity(cellcomplex, vertex).DumpDictionary())
        string += '"' + text + '" [color="#666666",style=filled];\n'
    for edge in edges_ptr:
        text0 = str(self.GetEntity(cellcomplex, edge.StartVertex()).DumpDictionary())
        text1 = str(self.GetEntity(cellcomplex, edge.EndVertex()).DumpDictionary())
        string += '"' + text0 + '"--"' + text1 + '"\n'
    string += "}"
    return string


setattr(topologic.Graph, "Circulation", Circulation)
setattr(topologic.Graph, "IsConnected", IsConnected)
setattr(topologic.Graph, "ShortestPathTable", ShortestPathTable)
setattr(topologic.Graph, "Separation", Separation)
setattr(topologic.Graph, "Faces", Faces)
setattr(topologic.Graph, "Cells", Cells)
setattr(topologic.Graph, "GetEntity", GetEntity)
setattr(topologic.Graph, "Dot", Dot)
