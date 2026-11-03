"""Overloads domain-specific methods onto topologic_core.Graph"""

import heapq
import topologic_core
from topologic_core import VertexUtility


def Circulation(self, cellcomplex):
    """Reduce an adjacency Graph to a circulation Graph.
    Uses heuristics for connecting rooms and floors between stair cells"""
    vertices_ptr = []
    # walls that can have a door, with the usages either side
    doors = []
    for face in self.Faces(cellcomplex):
        vertex = face.GraphVertex(self)
        if face.IsVertical():
            # wall
            axis = face.AxisOuter()
            if axis is None or VertexUtility.Distance(axis[0], axis[1]) < 1.0:
                # is too narrow for a door
                vertices_ptr.append(vertex)
            else:
                cells = face.Cells_Cached(cellcomplex)
                if cells[0].Elevation() != cells[1].Elevation():
                    # floors either side are not at the same level
                    vertices_ptr.append(vertex)
                else:
                    usages = [cells[0].Usage(), cells[1].Usage()]
                    if "void" in usages:
                        vertices_ptr.append(vertex)
                    else:
                        doors.append([vertex, cells, usages])

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
    public = ["stair", "circulation"]
    private = ["bedroom", "toilet"]
    # a toilet with no door to circulation is an en-suite
    toilets_public = set()
    for vertex, cells, usages in doors:
        for cell, usage, other in zip(cells, usages, reversed(usages)):
            if usage == "toilet" and other in public:
                toilets_public.add(cell.Get("index"))
    for vertex, cells, usages in doors:
        if sorted(usages) == ["bedroom", "toilet"]:
            toilet = cells[usages.index("toilet")]
            if toilet.Get("index") in toilets_public:
                vertices_ptr.append(vertex)
        elif (usages[0] in private and usages[1] not in public) or (
            usages[1] in private and usages[0] not in public
        ):
            vertices_ptr.append(vertex)
    # nobody goes to a 'void', an unreachable Cell would make the Graph disconnected
    all_vertices_ptr = []
    self.Vertices(all_vertices_ptr)
    for vertex in all_vertices_ptr:
        if (
            vertex.Get("class") == "Cell"
            and self.GetEntity(cellcomplex, vertex).Usage() == "void"
        ):
            vertices_ptr.append(vertex)
    self.RemoveVertices(vertices_ptr)
    self.PruneDoors(cellcomplex, doors, public)


def PruneDoors(self, cellcomplex, doors, public):
    """Rooms only want one door to circulation: a bedroom or toilet keeps the
    door to the least 'popular' circulation, a living room or kitchen to the
    most, where popular is the least 'separation' from all other Cells"""
    lookup = self.Lookup()
    separation = {}
    for key in lookup:
        if key[0] == "Cell":
            distances = _distances(lookup, key)
            others = [
                length
                for other, length in distances.items()
                if other[0] == "Cell" and other != key
            ]
            if others:
                separation[key[1]] = sum(others) / len(others)
    # walls between a room and circulation, by room
    rooms = {}
    for vertex, cells, usages in doors:
        key = ("Face", vertex.Get("index"))
        if key not in lookup:
            continue
        for cell, usage, other_cell, other in zip(
            cells, usages, reversed(cells), reversed(usages)
        ):
            if usage in ("bedroom", "toilet", "living", "kitchen") and other in public:
                index = cell.Get("index")
                if index not in rooms:
                    rooms[index] = [usage, []]
                rooms[index][1].append([key, other_cell.Get("index"), vertex])
    removed = []
    for index in sorted(rooms, key=int):
        usage, walls = rooms[index]
        if len(walls) < 2:
            continue
        sign = -1.0 if usage in ("bedroom", "toilet") else 1.0
        walls.sort(
            key=lambda wall: (
                sign * separation.get(wall[1], 0.0),
                int(wall[1]),
                int(wall[0][1]),
            )
        )
        for key, other, vertex in walls[1:]:
            neighbours = lookup.pop(key)
            for neighbour in neighbours:
                del lookup[neighbour][key]
            # keep a door to circulation that is only reached through this room
            if ("Cell", other) in _distances(lookup, ("Cell", index)):
                removed.append(vertex)
            else:
                lookup[key] = neighbours
                for neighbour, length in neighbours.items():
                    lookup[neighbour][key] = length
    self.RemoveVertices(removed)


def Lookup(self):
    """The Graph as a dictionary of Vertices, keyed by class and index, of
    adjacent Vertices and the length of the Edge to them"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    lookup = {(v.Get("class"), v.Get("index")): {} for v in vertices_ptr}
    edges_ptr = []
    self.Edges(edges_ptr)
    for edge in edges_ptr:
        start = edge.StartVertex()
        end = edge.EndVertex()
        a = (start.Get("class"), start.Get("index"))
        b = (end.Get("class"), end.Get("index"))
        if a in lookup and b in lookup:
            lookup[a][b] = edge.Length()
            lookup[b][a] = edge.Length()
    return lookup


def _distances(lookup, start):
    """Shortest path lengths from one Vertex in a Lookup() to those it reaches"""
    distances = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        distance, key = heapq.heappop(queue)
        if distance > distances[key]:
            continue
        for other, length in lookup[key].items():
            if other not in distances or distance + length < distances[other]:
                distances[other] = distance + length
                heapq.heappush(queue, (distance + length, other))
    return distances


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
        vertices_list = [v for v in vertices_ptr if v.Get("class") == "Cell"]
        for i in range(len(vertices_list)):
            for j in range(len(vertices_list)):
                if j <= i:
                    continue
                wire = self.ShortestPath(
                    vertices_list[i], vertices_list[j], "", "length"
                )
                edges_ptr = []
                wire.Edges(None, edges_ptr)
                length = sum(edge.Length() for edge in edges_ptr)
                i_index = vertices_list[i].Get("index")
                j_index = vertices_list[j].Get("index")
                if i_index not in result:
                    result[i_index] = {}
                if j_index not in result:
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
    else:
        # distances from an earlier Graph are no longer true
        vertices_ptr = []
        self.Vertices(vertices_ptr)
        for vertex in vertices_ptr:
            if vertex.Get("class") == "Cell":
                entity = self.GetEntity(cellcomplex, vertex)
                dictionary = entity.GetDictionary()
                if dictionary.ContainsKey("separation"):
                    dictionary.Remove("separation")
                    entity.SetDictionary(dictionary)


def Components(self):
    """Index numbers of Cells that can reach each other, as lists, largest first"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    unvisited = {(v.Get("class"), v.Get("index")): v for v in vertices_ptr}
    components = []
    while unvisited:
        stack = [unvisited.popitem()[1]]
        cells = []
        while stack:
            vertex = stack.pop()
            if vertex.Get("class") == "Cell":
                cells.append(vertex.Get("index"))
            adjacent_ptr = []
            self.AdjacentVertices(vertex, adjacent_ptr)
            for adjacent in adjacent_ptr:
                key = (adjacent.Get("class"), adjacent.Get("index"))
                if key in unvisited:
                    stack.append(unvisited.pop(key))
        if cells:
            components.append(sorted(cells, key=int))
    components.sort(key=lambda cells: (-len(cells), int(cells[0])))
    return components


def Faces(self, cellcomplex):
    """Return all the Faces from a CellComplex corresponding to this Graph"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    faces_ptr = [
        self.GetEntity(cellcomplex, vertex)
        for vertex in vertices_ptr
        if vertex.Get("class") == "Face"
    ]
    return faces_ptr


def Cells(self, cellcomplex):
    """Return all the Cells from a CellComplex corresponding to this Graph"""
    vertices_ptr = []
    self.Vertices(vertices_ptr)
    cells_ptr = [
        self.GetEntity(cellcomplex, vertex)
        for vertex in vertices_ptr
        if vertex.Get("class") == "Cell"
    ]
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


setattr(topologic_core.Graph, "Circulation", Circulation)
setattr(topologic_core.Graph, "PruneDoors", PruneDoors)
setattr(topologic_core.Graph, "Lookup", Lookup)
setattr(topologic_core.Graph, "IsConnected", IsConnected)
setattr(topologic_core.Graph, "ShortestPathTable", ShortestPathTable)
setattr(topologic_core.Graph, "Separation", Separation)
setattr(topologic_core.Graph, "Components", Components)
setattr(topologic_core.Graph, "Faces", Faces)
setattr(topologic_core.Graph, "Cells", Cells)
setattr(topologic_core.Graph, "GetEntity", GetEntity)
setattr(topologic_core.Graph, "Dot", Dot)
