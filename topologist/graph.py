import topologic
from topologic import Vertex, Face, Cell, Graph, VertexUtility
from topologist.helpers import create_stl_list

def Adjacency(cellcomplex):
    """Index all cells and faces, return a circulation graph with the same indexing"""
    """Adjacency graph has nodes for cells, and nodes for faces that connect them"""
    cells = create_stl_list(Cell)
    cellcomplex.Cells(cells)
    index = 0
    for cell in cells:
        cell.Set('index', str(index))
        cell.Set('class', 'Cell')
        index += 1

    faces = create_stl_list(Face)
    cellcomplex.Faces(faces)
    index = 0
    for face in faces:
        face.Set('index', str(index))
        face.Set('class', 'Face')
        index += 1

    # a graph where each cell and face between them has a vertex
    graph = Graph.ByTopology(cellcomplex, False, True, False, False, False, False, 0.0001)
    return graph

def Circulation(self, cellcomplex):
    """Reduce adjacency graph to a circulation graph"""
    vertices = create_stl_list(Vertex)
    for face in self.Faces(cellcomplex):
        vertex = face.GraphVertex(self)
        if face.IsVertical():
            # wall
            axis = face.AxisOuter()
            if VertexUtility.Distance(axis[0], axis[1]) < 1.0:
                # is too narrow for a door
                vertices.push_back(vertex)
            else:
                cells = create_stl_list(Cell)
                face.Cells(cells)
                cells = list(cells)
                if cells[0].Elevation() != cells[1].Elevation():
                    # floors either side are not at the same level
                    vertices.push_back(vertex)
                else:
                    usage_a = cells[0].Usage()
                    usage_b = cells[1].Usage()
                    if (usage_a == 'bedroom' or usage_a == 'toilet') and not (usage_b == 'stair' or usage_b == 'circulation'):
                        vertices.push_back(vertex)
                    elif (usage_b == 'bedroom' or usage_b == 'toilet') and not (usage_a == 'stair' or usage_a == 'circulation'):
                        vertices.push_back(vertex)

        elif face.IsHorizontal():
            # floor
            cells = create_stl_list(Cell)
            face.Cells(cells)
            if len(cells) == 2 and list(cells)[0].Usage() == 'stair' and list(cells)[1].Usage() == 'stair':
                continue
            # is not in a stair flight
            vertices.push_back(vertex)
        else:
            # neither vertical or horizontal
            vertices.push_back(vertex)
    self.RemoveVertices(vertices)

def IsConnected(self):
    """Checks that all Vertices can be reached from all other Vertices"""
    connected = True
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    vertex_a = list(vertices)[0]
    for vertex_b in vertices:
        if vertex_b.Get('class') == 'Face': continue
        if vertex_a.IsSame(vertex_b): continue
        distance = self.TopologicalDistance(vertex_a, vertex_b)
        if distance > 255: connected = False
    return connected

def Faces(self, cellcomplex):
    """Return all the Faces from a CellComplex corresponding to this Graph"""
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    faces = create_stl_list(Face)
    for vertex in vertices:
        if vertex.Get('class') == 'Face':
            face = self.GetEntity(cellcomplex, vertex)
            faces.push_back(face)
    return faces

def Cells(self, cellcomplex):
    """Return all the Cells from a CellComplex corresponding to this Graph"""
    vertices = create_stl_list(Vertex)
    self.Vertices(vertices)
    cells = create_stl_list(Cell)
    for vertex in vertices:
        if vertex.Get('class') == 'Cell':
            cell = self.GetEntity(cellcomplex, vertex)
            cells.push_back(cell)
    return cells

def GetEntity(self, cellcomplex, vertex):
    """Return the entity from a CellComplex (Face or Cell) corresponding to this Vertex)"""
    index = vertex.Get('index')
    if vertex.Get('class') == 'Face':
        entities = create_stl_list(Face)
        cellcomplex.Faces(entities)
    elif vertex.Get('class') == 'Cell':
        entities = create_stl_list(Cell)
        cellcomplex.Cells(entities)
    else: return None
    for entity in entities:
        if entity.Get('index') == index:
            return entity

setattr(topologic.Graph, 'Adjacency', Adjacency)
setattr(topologic.Graph, 'Circulation', Circulation)
setattr(topologic.Graph, 'IsConnected', IsConnected)
setattr(topologic.Graph, 'Faces', Faces)
setattr(topologic.Graph, 'Cells', Cells)
setattr(topologic.Graph, 'GetEntity', GetEntity)
