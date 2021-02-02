import sys

sys.path.append('/home/bruno/src/topologicPy/cpython')
sys.path.append('/home/bruno/src/homemaker-addon')

from topologic import Vertex, Edge, Face, CellComplex
from topologist.helpers import create_stl_list, vertex_index, el

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

            walls_external = cc.WallsExternal()
            for elevation in walls_external:
                for height in walls_external[elevation]:
                    wire = walls_external[elevation][height]
                    vertices_stl = create_stl_list(Vertex)
                    wire.Vertices(vertices_stl)
                    edges_stl = create_stl_list(Edge)
                    wire.Edges(edges_stl)

                    vertices = []
                    for vertex in vertices_stl:
                        vertices.append([vertex.X(), vertex.Y(), vertex.Z()])

                    edges = []
                    for edge in edges_stl:
                        edges.append([vertex_index(edge.StartVertex(), vertices_stl),
                                      vertex_index(edge.EndVertex(), vertices_stl)])

                    my_name = 'Wire ' + str(elevation) + '+' + str(height)
                    mesh = bpy.data.meshes.new(name =  my_name)
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
