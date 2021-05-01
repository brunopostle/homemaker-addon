import sys
import os
import re

sys.path.append("/home/bruno/src/homemaker-addon")
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from topologic import Vertex, Face, CellComplex, Graph
from topologist.helpers import create_stl_list
from molior import Molior
import molior.ifc

import tempfile
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
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bl_objects = []
        widgets = []

        for blender_object in context.selected_objects:
            if not blender_object.type == "MESH":
                continue
            # Collect widgets (if any) for allocating room/space usage
            label = re.match(
                "(bedroom|circulation|circulation_stair|stair|kitchen|living|retail|sahn|toilet)",
                blender_object.name,
                flags=re.IGNORECASE,
            )
            if label:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                blender_object = blender_object.evaluated_get(depsgraph)
                bm = bmesh.new()  # create an empty BMesh
                bm.from_mesh(blender_object.data)  # fill it in from a Mesh
                bm.verts.ensure_lookup_table()

                centre = [0.0, 0.0, 0.0]
                total = len(bm.verts)
                for v in bm.verts:
                    coor = v.co[:]
                    centre[0] += coor[0]
                    centre[1] += coor[1]
                    centre[2] += coor[2]
                vertex = Vertex.ByCoordinates(
                    centre[0] / total, centre[1] / total, centre[2] / total
                )
                widgets.append([label[0], vertex])
            else:
                bl_objects.append(blender_object)

        # Each remaining mesh becomes a separate building
        # FIXME should all end-up in the same IfcProject
        for bl_object in bl_objects:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            bl_object = bl_object.evaluated_get(depsgraph)
            # Get a BMesh representation
            bm = bmesh.new()  # create an empty BMesh
            bm.from_mesh(bl_object.data)  # fill it in from a Mesh
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bm.verts.ensure_lookup_table()

            # Topologic model
            vertices = []

            for v in bm.verts:
                coor = v.co[:]
                vertex = Vertex.ByCoordinates(coor[0], coor[1], coor[2])
                vertices.append(vertex)

            faces_ptr = create_stl_list(Face)

            for f in bm.faces:
                stylename = "default"
                if len(bl_object.material_slots) > 0:
                    stylename = bl_object.material_slots[f.material_index].material.name
                vertices_face = []
                for v in f.verts:
                    vertex = vertices[v.index]
                    vertices_face.append(vertex)
                face = Face.ByVertices(vertices_face)
                face.Set("stylename", stylename)
                faces_ptr.push_back(face)
            bl_object.hide_viewport = True

            # Generate a Topologic CellComplex
            cc = CellComplex.ByFaces(faces_ptr, 0.0001)
            # Copy styles from Faces to the CellComplex
            cc.ApplyDictionary(faces_ptr)
            # Assign Cell usages from widgets
            cc.AllocateCells(widgets)
            # Collect unique elevations and assign storey numbers
            elevations = cc.Elevations()
            # Generate a cirulation Graph
            circulation = Graph.Adjacency(cc)
            circulation.Circulation(cc)
            # print(circulation.Dot(cc))

            # FIXME this isn't creating any IFC data
            # TODO should also do soffits, ceilings etc.
            roof = cc.Roof()
            if roof:
                vertices, faces = roof.Mesh()

                mesh = bpy.data.meshes.new(name="Roof")
                mesh.from_pydata(vertices, [], faces)
                obj = object_data_add(context, mesh)
                modifier = obj.modifiers.new("Roof Thickness", "SOLIDIFY")
                modifier.use_even_offset = True
                modifier.thickness = -0.1

            # generate an IFC object
            ifc = molior.ifc.init(bl_object.name, elevations)

            # Traces are 2D paths that define walls, extrusions and rooms
            traces = cc.GetTraces().traces

            molior_object = Molior()
            molior_object.Process(ifc, circulation, elevations, traces)

            # FIXME shouldn't have to write and import an IFC file
            ifc_tmp = tempfile.NamedTemporaryFile(
                mode="w+b", suffix=".ifc", delete=False
            )
            ifc.write(ifc_tmp.name)
            logger = logging.getLogger("ImportIFC")

            ifc_import_settings = import_ifc.IfcImportSettings.factory(
                bpy.context, ifc_tmp.name, logger
            )
            ifc_importer = import_ifc.IfcImporter(ifc_import_settings)
            ifc_importer.execute()
        return {"FINISHED"}


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
