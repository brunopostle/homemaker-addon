import sys

sys.path.append('/home/bruno/src/topologicPy/cpython')
sys.path.append('/home/bruno/src/homemaker-addon')

from topologic import Vertex, Cell, Face, CellComplex
from topologist.helpers import create_stl_list, string_to_coor_2d, vertex_id
from molior import Wall, Extrusion, Space, Stair, Floor, Ceiling

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
                style = 'default'
                if len(bl_object.material_slots) > 0:
                    style = bl_object.material_slots[f.material_index].material.name
                vertices_face = []
                for v in f.verts:
                    vertex = vertices[v.index]
                    vertices_face.append(vertex)
                face = Face.ByVertices(vertices_face)
                face.Set('style', style)
                faces.append(face)
            bpy.ops.object.hide_view_set(unselected=False)

            # TODO assign room usages

            # start using Topologic
            faces_ptr = create_stl_list(Face)
            for face in faces:
                faces_ptr.push_back(face)

            cc = CellComplex.ByFaces(faces_ptr, 0.0001)
            elevations = cc.Elevations()

            # TODO build and prune circulation graph

            # TODO read MOLIOR_STYLE from env
            style = 'default'

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
                modifier.thickness = -0.1

            # walls
            walls = cc.Walls()

            # external walls
            chains = walls['external']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            closed = 0
                            if chain.is_simple_cycle(): closed = 1
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Wall({'closed': closed,
                                           'path': path,
                                           'name': 'exterior',
                                      'elevation': elevation,
                                         'height': height,
                                      'extension': 0.25,
                                          'style': style,
                                          'level': elevations[elevation]})

                            edges = chain.edges()
                            for segment in range(len(part.openings)):
                                edge = chain.graph[edges[segment][0]]
                                face = edge[1][2]
                                interior_type = face.UsageInside()
                                part.populate_exterior_openings(segment, interior_type, 0)
                            molior.append(part.__dict__)

            # external walls unsupported
            chains = walls['external_unsupported']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            closed = 0
                            if chain.is_simple_cycle(): closed = 1
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Extrusion({'closed': closed,
                                                'path': path,
                                                'name': 'ground beam',
                                           'elevation': elevation,
                                              'height': 0.0,
                                               'style': style,
                                               'level': elevations[elevation]})
                            molior.append(part.__dict__)

            # internal walls
            chains = walls['internal']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Wall({'closed': 0,
                                           'path': path,
                                           'name': 'interior',
                                      'elevation': elevation,
                                        'ceiling': 0.2,
                                          'inner': 0.08,
                                          'outer': 0.08,
                                         'height': height,
                                      'extension': 0.0,
                                          'style': style,
                                          'level': elevations[elevation]})
                            edge = chain.graph[chain.edges()[0][0]]
                            face = edge[1][2]
                            usages = face.Usages()
                            part.populate_interior_openings(0, usages[0], usages[1], 0)
                            molior.append(part.__dict__)

            # internal walls unsupported
            chains = walls['internal_unsupported']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Extrusion({'closed': 0,
                                                'path': path,
                                                'name': 'ground beam',
                                           'elevation': elevation,
                                              'height': 0.0,
                                               'style': style,
                                               'level': elevations[elevation]})
                            molior.append(part.__dict__)

            # eaves
            # TODO need separate parapet chain where roof is flat
            chains = walls['eaves']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            closed = 0
                            name = 'parapet'
                            if chain.is_simple_cycle():
                                closed = 1
                                name = 'eaves'
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Extrusion({'closed': closed,
                                                'path': path,
                                                'name': name,
                                           'elevation': elevation,
                                               'style': style,
                                               'level': elevations[elevation]})
                            molior.append(part.__dict__)

            # open walls, where both sides are 'outside'
            chains = walls['open']
            for elevation in chains:
                for height in chains[elevation]:
                    for style in chains[elevation][height]:
                        for chain in chains[elevation][height][style]:
                            closed = 0
                            if chain.is_simple_cycle(): closed = 1
                            path = []
                            for node in chain.nodes():
                                path.append(string_to_coor_2d(node))
                            part = Extrusion({'closed': closed,
                                                'path': path,
                                                'name': 'external beam',
                                              'height': height,
                                           'elevation': elevation,
                                               'style': style,
                                               'level': elevations[elevation]})
                            molior.append(part.__dict__)
                            # TODO corner and intermediate beam columns

            # rooms
            cells = create_stl_list(Cell)
            cc.Cells(cells)
            number = 0
            for cell in cells:
                perimeter = cell.Perimeter()
                if perimeter == None or len(perimeter) == 0:
                    continue
                colour = 0
                if not cell.IsOutside():
                    crinkliness = cell.Crinkliness()
                    colour = (int(crinkliness*16)-7)*10
                    if colour > 170: colour = 170
                    if colour < 10: colour = 10
                elevation = cell.Elevation()
                height = cell.Height()
                usage = cell.Usage()
                path = []
                for vertex in perimeter:
                    path.append([vertex.X(), vertex.Y()])

                part = Space({'path': path,
                                'id': number,
                              'name': 'my room',
                         'elevation': elevation,
                            'height': height,
                             'level': elevations[elevation],
                            'colour': colour,
                             'usage': usage})
                molior.append(part.__dict__)

                part = Stair({'path': path,
                                'id': number,
                              'name': 'my room',
                         'elevation': elevation,
                            'height': height,
                             'style': style,
                             'level': elevations[elevation],
                            'risers': int(height/0.19)+1,
                             'usage': usage})
                if usage == 'Circulation_Stair' and len(path) == 4 and cell.CellsAbove():
                    molior.append(part.__dict__)

                part = Floor({'path': path,
                                'id': number,
                              'name': 'my room',
                         'elevation': elevation,
                             'style': style,
                             'level': elevations[elevation]})
                if not (usage == 'Circulation_Stair' and cell.CellsBelow()):
                    molior.append(part.__dict__)

                part = Ceiling({'path': path,
                                  'id': number,
                                'name': 'my room',
                           'elevation': elevation,
                              'height': height,
                               'style': style,
                               'level': elevations[elevation]})
                if not (usage == 'Circulation_Stair' and cell.CellsAbove()):
                    molior.append(part.__dict__)

                number += 1

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
