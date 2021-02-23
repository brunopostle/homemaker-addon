import sys

sys.path.append('/home/bruno/src/topologicPy/cpython')
sys.path.append('/home/bruno/src/homemaker-addon')

from topologic import Vertex, Cell, Face, CellComplex
from topologist.helpers import create_stl_list, init_stl_lists, string_to_coor_2d, vertex_id
from molior import Wall, Extrusion

import datetime
import tempfile
import yaml
import subprocess
import logging
from blenderbim import import_ifc
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

            # Topologic model
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

            # start using Topologic
            init_stl_lists()

            faces_ptr = create_stl_list(Face)
            for face in faces:
                faces_ptr.push_back(face)

            cc = CellComplex.ByFaces(faces_ptr, 0.0001)
            elevations = cc.Elevations()

            # molior
            molior = []
            molior_tmp = tempfile.NamedTemporaryFile(mode='w+b', suffix='.molior', delete=False)
            ifc_tmp = tempfile.NamedTemporaryFile(mode='w+b', suffix='.ifc', delete=False)

            # roof
            roof = cc.Roof()
            if roof:
                vertices_stl = create_stl_list(Vertex)
                roof.Vertices(vertices_stl)
                vertices = []
                for vertex in vertices_stl:
                    vertices.append([vertex.X(), vertex.Y(), vertex.Z()])

                faces_stl = create_stl_list(Face)
                roof.Faces(faces_stl)
                faces = []

                for face in faces_stl:
                    wire = face.ExternalBoundary()
                    vertices_wire = create_stl_list(Vertex)
                    wire.Vertices(vertices_wire)
                    face_tmp = []
                    for vertex in vertices_wire:
                        face_tmp.append(vertex_id(roof, vertex))
                    faces.append(face_tmp)

                mesh = bpy.data.meshes.new(name="Roof")
                mesh.from_pydata(vertices, [], faces)
                obj = object_data_add(context, mesh)
                modifier = obj.modifiers.new("Roof Thickness", "SOLIDIFY")
                modifier.use_even_offset = True
                modifier.thickness = -0.2

            # walls
            walls = cc.Walls()

            # external walls
            walls_external = walls['external']
            for elevation in walls_external:
                for height in walls_external[elevation]:
                    for chain in walls_external[elevation][height]:
                        closed = 0
                        if chain.is_simple_cycle(): closed = 1
                        path = []
                        for node in chain.nodes():
                            path.append(string_to_coor_2d(node))
                        wall = Wall({'closed': closed,
                                       'path': path,
                                       'name': 'exterior',
                                  'elevation': elevation,
                                     'height': height,
                                  'extension': 0.25,
                                      'level': elevations[elevation]})

                        for segment in range(len(wall.openings)):
                            interior_type = 'Living' # FIXME
                            wall.populate_exterior_openings(segment, interior_type, 0)
                        molior.append(wall.__dict__)

            # internal walls
            walls_internal = walls['internal']
            for elevation in walls_internal:
                for height in walls_internal[elevation]:
                    for chain in walls_internal[elevation][height]:
                        path = []
                        for node in chain.nodes():
                            path.append(string_to_coor_2d(node))
                        wall = Wall({'closed': 0,
                                       'path': path,
                                       'name': 'interior',
                                  'elevation': elevation,
                                    'ceiling': 0.2,
                                      'inner': 0.08,
                                      'outer': 0.08,
                                     'height': height,
                                  'extension': 0.0,
                                      'level': elevations[elevation]})
                        for segment in range(len(wall.openings)):
                            type_a = 'Living' # FIXME
                            type_b = 'Living' # FIXME
                            wall.populate_interior_openings(segment, type_a, type_b, 0)
                        molior.append(wall.__dict__)

            # eaves
            walls_eaves = walls['eaves']
            for elevation in walls_eaves:
                for height in walls_eaves[elevation]:
                    for chain in walls_eaves[elevation][height]:
                        closed = 0
                        name = 'parapet'
                        if chain.is_simple_cycle():
                            closed = 1
                            name = 'eaves'
                        path = []
                        for node in chain.nodes():
                            path.append(string_to_coor_2d(node))
                        wall = Extrusion({'closed': closed,
                                            'path': path,
                                            'name': name,
                                       'elevation': elevation,
                                           'level': elevations[elevation]})
                        molior.append(wall.__dict__)

            # open walls, where both sides are 'outside'
            walls_open = walls['open']
            for elevation in walls_open:
                for height in walls_open[elevation]:
                    for chain in walls_open[elevation][height]:
                        closed = 0
                        if chain.is_simple_cycle(): closed = 1
                        path = []
                        for node in chain.nodes():
                            path.append(string_to_coor_2d(node))
                        wall = Extrusion({'closed': closed,
                                            'path': path,
                                            'name': 'external-beam',
                                          'height': height,
                                       'elevation': elevation,
                                           'level': elevations[elevation]})
                        molior.append(wall.__dict__)

            # rooms
            cells = create_stl_list(Cell)
            cc.Cells(cells)
            for cell in cells:
                perimeter = cell.Perimeter()
                if len(perimeter) == 0:
                    continue
                vertices = []
                for v in perimeter:
                    vertices.append([v.X(), v.Y(), v.Z()])
                mesh = bpy.data.meshes.new(name="Floor")
                mesh.from_pydata(vertices, [], [list(range(len(vertices)))])
                obj = object_data_add(context, mesh)
                modifier = obj.modifiers.new("Floor Thickness", "SOLIDIFY")
                modifier.use_even_offset = True
                modifier.thickness = 0.2

        # molior
        with open(molior_tmp.name, 'w') as outfile:
            yaml.dump_all(molior, outfile)
        subprocess.call(['molior-ifc.pl', molior_tmp.name, ifc_tmp.name])
        logger = logging.getLogger('ImportIFC')

        ifc_import_settings = import_ifc.IfcImportSettings.factory(bpy.context, ifc_tmp.name, logger)
        ifc_importer = import_ifc.IfcImporter(ifc_import_settings)
        ifc_importer.execute()
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
