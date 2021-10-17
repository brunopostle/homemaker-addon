"""Overloads domain-specific methods onto topologic.Graph"""

import topologic
from topologic import Vertex, Edge, Face, Cell, Graph, VertexUtility
from topologist.helpers import create_stl_list


def Adjacency(cellcomplex):
    """Index all cells and faces, return a circulation graph with the same indexing"""
    """Adjacency graph has nodes for cells, and nodes for faces that connect them"""
    cells_ptr = create_stl_list(Cell)
    cellcomplex.Cells(cells_ptr)
    index = 0
    for cell in cells_ptr:
        cell.Set("index", str(index))
        cell.Set("class", "Cell")
        index += 1

    faces_ptr = create_stl_list(Face)
    cellcomplex.Faces(faces_ptr)
    index = 0
    for face in faces_ptr:
        face.Set("index", str(index))
        face.Set("class", "Face")
        index += 1

    # a graph where each cell and face between them has a vertex
    graph = Graph.ByTopology(
        cellcomplex, False, True, False, False, False, False, 0.0001
    )
    return graph


def Circulation(self, cellcomplex):
    """Reduce adjacency graph to a circulation graph"""
    vertices_ptr = create_stl_list(Vertex)
    for face in self.Faces(cellcomplex):
        vertex = face.GraphVertex(self)
        if face.IsVertical():
            # wall
            axis = face.AxisOuter()
            if VertexUtility.Distance(axis[0], axis[1]) < 1.0:
                # is too narrow for a door
                vertices_ptr.push_back(vertex)
            else:
                cells_ptr = create_stl_list(Cell)
                face.Cells(cells_ptr)
                cells = list(cells_ptr)
                if cells[0].Elevation() != cells[1].Elevation():
                    # floors either side are not at the same level
                    vertices_ptr.push_back(vertex)
                else:
                    usage_a = cells[0].Usage()
                    usage_b = cells[1].Usage()
                    if (usage_a == "bedroom" or usage_a == "toilet") and not (
                        usage_b == "stair" or usage_b == "circulation"
                    ):
                        vertices_ptr.push_back(vertex)
                    elif (usage_b == "bedroom" or usage_b == "toilet") and not (
                        usage_a == "stair" or usage_a == "circulation"
                    ):
                        vertices_ptr.push_back(vertex)

        elif face.IsHorizontal():
            # floor
            cells_ptr = create_stl_list(Cell)
            face.Cells(cells_ptr)
            if (
                len(cells_ptr) == 2
                and list(cells_ptr)[0].Usage() == "stair"
                and list(cells_ptr)[1].Usage() == "stair"
            ):
                continue
            # is not in a stair flight
            vertices_ptr.push_back(vertex)
        else:
            # neither vertical or horizontal
            vertices_ptr.push_back(vertex)
    self.RemoveVertices(vertices_ptr)


def IsConnected(self):
    """Checks that all Vertices can be reached from all other Vertices"""
    connected = True
    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)
    vertex_a = list(vertices_ptr)[0]
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
    if not self.IsConnected():
        return result
    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)
    vertices_list = []
    for vertex in list(vertices_ptr):
        if vertex.Get("class") == "Cell":
            vertices_list.append(vertex)
    for i in range(len(vertices_list)):
        for j in range(len(vertices_list)):
            if j <= i:
                continue
            wire = self.ShortestPath(vertices_list[i], vertices_list[j], "", "length")
            edges_ptr = create_stl_list(Edge)
            wire.Edges(edges_ptr)
            length = 0.0
            for edge in list(edges_ptr):
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


def Connectedness(self, table):
    """Tags 'cell' vertices with average travel distance to all other cells"""
    if table == {}:
        return
    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)
    for vertex in list(vertices_ptr):
        if vertex.Get("class") == "Cell":
            index = vertex.Get("index")
            total_length = 0.0
            for length in table[index].values():
                total_length += length
            vertex.Set("connectedness", str(total_length / len(table[index])))


def Faces(self, cellcomplex):
    """Return all the Faces from a CellComplex corresponding to this Graph"""
    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)
    faces_ptr = create_stl_list(Face)
    for vertex in vertices_ptr:
        if vertex.Get("class") == "Face":
            face = self.GetEntity(cellcomplex, vertex)
            faces_ptr.push_back(face)
    return faces_ptr


def Cells(self, cellcomplex):
    """Return all the Cells from a CellComplex corresponding to this Graph"""
    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)
    cells_ptr = create_stl_list(Cell)
    for vertex in vertices_ptr:
        if vertex.Get("class") == "Cell":
            cell = self.GetEntity(cellcomplex, vertex)
            cells_ptr.push_back(cell)
    return cells_ptr


def GetEntity(self, cellcomplex, vertex):
    """Return the entity from a CellComplex (Face or Cell) corresponding to this Vertex)"""
    index = vertex.Get("index")
    if vertex.Get("class") == "Face":
        topologies_ptr = create_stl_list(Face)
        cellcomplex.Faces(topologies_ptr)
    elif vertex.Get("class") == "Cell":
        topologies_ptr = create_stl_list(Cell)
        cellcomplex.Cells(topologies_ptr)
    else:
        return None
    for entity in topologies_ptr:
        if entity.Get("index") == index:
            return entity


def Dot(self, cellcomplex):
    """A generic GraphViz .dot file"""
    # neato -Tpng < graph.dot > graph.png
    string = "strict graph G {\n"
    string += "graph [overlap=false];\n"

    vertices_ptr = create_stl_list(Vertex)
    self.Vertices(vertices_ptr)

    edges_ptr = create_stl_list(Edge)
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


setattr(topologic.Graph, "Adjacency", Adjacency)
setattr(topologic.Graph, "Circulation", Circulation)
setattr(topologic.Graph, "IsConnected", IsConnected)
setattr(topologic.Graph, "ShortestPathTable", ShortestPathTable)
setattr(topologic.Graph, "Connectedness", Connectedness)
setattr(topologic.Graph, "Faces", Faces)
setattr(topologic.Graph, "Cells", Cells)
setattr(topologic.Graph, "GetEntity", GetEntity)
setattr(topologic.Graph, "Dot", Dot)
