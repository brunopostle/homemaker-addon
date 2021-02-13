import sys

sys.path.append('/home/bruno/src/topologicPy/cpython')
sys.path.append('/home/bruno/src/homemaker-addon')

from topologic import Vertex, Edge, Cell, Face, CellComplex, Graph
from topologist.helpers import create_stl_list, string_to_coor, el

import datetime
import bpy
import bmesh
from bpy_extras.object_utils import object_data_add

bl_info = {
    "name": "Homemaker Topologise",
    "blender": (2, 80, 0),
    "category": "Object",
}

class ObjectHomemaker(bpy.types.Operator):
    """Object Homemaker Topologise"""
    bl_idname = "object.homemaker"
    bl_label = "Homemaker Topologise"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for bl_object in context.selected_objects:

            print('start ' + str(datetime.datetime.now()))
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bl_object = bl_object.evaluated_get(depsgraph)
            # Get a BMesh representation
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(bl_object.data)   # fill it in from a Mesh
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bm.verts.ensure_lookup_table()

            vertices = []

            for v in bm.verts:
                coor = v.co[:]
                vertex = Vertex.ByCoordinates(coor[0], coor[1], coor[2])
                vertices.append(vertex)

            faces = []

            for f in bm.faces:
                vertices_face = []
                for v in f.verts:
                    vertex = vertices[v.index]
                    vertices_face.append(vertex)
                face = Face.ByVertices(vertices_face)
                faces.append(face)
            bpy.ops.object.hide_view_set(unselected=False)

            faces_ptr = create_stl_list(Face)
            for face in faces:
                faces_ptr.push_back(face)
            print('cellcomplex start ' + str(datetime.datetime.now()))
            cc = CellComplex.ByFaces(faces_ptr, 0.0001)
            print('cellcomplex created ' + str(datetime.datetime.now()))

            walls = cc.Walls()
            print('wall graphs created ' + str(datetime.datetime.now()))
            walls_external = walls['external']
            for elevation in walls_external:
                for height in walls_external[elevation]:
                    graph = walls_external[elevation][height]

                    for acycle in graph.find_chains():
                        vertices = []
                        for node in acycle.nodes():
                            vertices.append(string_to_coor(node))

                        edges = []
                        for index in range(len(vertices) -1):
                            edges.append([index, index +1])

                        my_name = str(elevation) + '+' + str(height) + ' Acycle'

                        # copied from blenderbim 'dumb wall'
                        mesh = bpy.data.meshes.new(name="Dumb Wall")
                        mesh.from_pydata(vertices, edges, [])
                        obj = object_data_add(context, mesh)
                        modifier = obj.modifiers.new("Wall Height", "SCREW")
                        modifier.angle = 0
                        modifier.screw_offset = height
                        modifier.use_smooth_shade = False
                        modifier.use_normal_calculate = True
                        modifier.use_normal_flip = False
                        modifier.steps = 1
                        modifier.render_steps = 1
                        modifier = obj.modifiers.new("Wall Width", "SOLIDIFY")
                        modifier.use_even_offset = True
                        modifier.thickness = 0.33
                        modifier.offset = -0.48484848
                        obj.name = "Wall " + my_name

                    for cycle in graph.find_cycles():
                        vertices = []
                        for node in cycle.nodes():
                            vertices.append(string_to_coor(node))

                        edges = []
                        for index in range(len(vertices) -1):
                            edges.append([index, index +1])
                        edges.append([len(vertices) -1, 0])

                        my_name = str(elevation) + '+' + str(height) + ' Cycle'

                        # copied from blenderbim 'dumb wall'
                        mesh = bpy.data.meshes.new(name="Dumb Wall")
                        mesh.from_pydata(vertices, edges, [])
                        obj = object_data_add(context, mesh)
                        modifier = obj.modifiers.new("Wall Height", "SCREW")
                        modifier.angle = 0
                        modifier.screw_offset = height
                        modifier.use_smooth_shade = False
                        modifier.use_normal_calculate = True
                        modifier.use_normal_flip = False
                        modifier.steps = 1
                        modifier.render_steps = 1
                        modifier = obj.modifiers.new("Wall Width", "SOLIDIFY")
                        modifier.use_even_offset = True
                        modifier.thickness = 0.33
                        modifier.offset = -0.48484848
                        obj.name = "Wall " + my_name

            print('external walls created ' + str(datetime.datetime.now()))
            walls_internal = walls['internal']
            for elevation in walls_internal:
                for height in walls_internal[elevation]:
                    simple = walls_internal[elevation][height]

                    for edge in simple:
                        my_name = str(elevation) + '+' + str(height) + ' Internal'

                        # copied from blenderbim 'dumb wall'
                        mesh = bpy.data.meshes.new(name="Dumb Wall")
                        mesh.from_pydata([string_to_coor(edge[0]), string_to_coor(edge[1])], [[0, 1]], [])
                        obj = object_data_add(context, mesh)
                        modifier = obj.modifiers.new("Wall Height", "SCREW")
                        modifier.angle = 0
                        modifier.screw_offset = height
                        modifier.use_smooth_shade = False
                        modifier.use_normal_calculate = True
                        modifier.use_normal_flip = False
                        modifier.steps = 1
                        modifier.render_steps = 1
                        modifier = obj.modifiers.new("Wall Width", "SOLIDIFY")
                        modifier.use_even_offset = True
                        modifier.thickness = 0.16
                        modifier.offset = 0.0
                        obj.name = "Wall " + my_name

            print('internal walls created ' + str(datetime.datetime.now()))
            cells = create_stl_list(Cell)
            cc.Cells(cells)
            for cell in cells:
                perimeter = cell.Perimeter()
                vertices = []
                for v in perimeter:
                    vertices.append([v.X(), v.Y(), v.Z()])
                mesh = bpy.data.meshes.new(name="Floor")
                mesh.from_pydata(vertices, [], [list(range(len(vertices)))])
                obj = object_data_add(context, mesh)
                modifier = obj.modifiers.new("Floor Thickness", "SOLIDIFY")
                modifier.use_even_offset = True
                modifier.thickness = 0.2

            print('floors created' + str(datetime.datetime.now()))
            graph = Graph.ByTopology(cc, True, False, False, False, False, False, 0.0001)
            topology = graph.Topology()
            edges = create_stl_list(Edge)
            topology.Edges(edges)
            for edge in edges:
                start = edge.StartVertex()
                end = edge.EndVertex()
                vertices = [[start.X(), start.Y(), start.Z()],
                            [end.X(), end.Y(), end.Z()]]

                mesh = bpy.data.meshes.new(name='Graph')
                mesh.from_pydata(vertices, [[0, 1]], [])
                object_data_add(context, mesh)
            print('internal connectivity created ' + str(datetime.datetime.now()))

        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(ObjectHomemaker.bl_idname)

def register():
    bpy.utils.register_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
