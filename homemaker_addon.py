import sys

sys.path.append('/home/bruno/src/topologicPy/cpython')
sys.path.append('/home/bruno/src/homemaker-addon')

from topologic import Vertex, Face, CellComplex
from topologist.helpers import create_stl_list, string_to_coor, el, nx_acycles

import networkx as nx
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
                vertex = Vertex.ByCoordinates(coor[0], coor[1], el(coor[2]))
                vertices.append(vertex)

            faces = []

            for f in bm.faces:
                vertices_face = []
                for v in f.verts:
                    vertex = vertices[v.index]
                    vertices_face.append(vertex)
                face = Face.ByVertices(vertices_face)
                faces.append(face)

            faces_ptr = create_stl_list(Face)
            for face in faces:
                faces_ptr.push_back(face)
            cc = CellComplex.ByFaces(faces_ptr, 0.0001)

            walls = cc.Walls()
            walls_external = walls['external']
            for elevation in walls_external:
                for height in walls_external[elevation]:
                    graph = walls_external[elevation][height]

                    cycles = nx.simple_cycles(graph)
                    for cycle in cycles:
                        vertices = []
                        for node in cycle:
                            vertices.append(string_to_coor(node))

                        edges = []
                        for index in range(len(vertices) -1):
                            edges.append([index, index +1])
                        edges.append([len(vertices) -1, 0])

                        my_name = str(elevation) + '+' + str(height) + ' Cycle'
                        mesh = bpy.data.meshes.new(name=my_name)
                        mesh.from_pydata(vertices, edges, [])
                        object_data_add(context, mesh)

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
                        modifier.thickness = 0.37
                        obj.name = "Wall"

                    for acycle in nx_acycles(graph):
                        vertices = []
                        for node in acycle:
                            vertices.append(string_to_coor(node))

                        edges = []
                        for index in range(len(vertices) -1):
                            edges.append([index, index +1])

                        my_name = str(elevation) + '+' + str(height) + ' Acycle'
                        mesh = bpy.data.meshes.new(name=my_name)
                        mesh.from_pydata(vertices, edges, [])
                        object_data_add(context, mesh)

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
