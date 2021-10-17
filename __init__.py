import sys
import os
import re

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append("/home/bruno/src/homemaker-addon")
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/libs/site/packages"))

from topologic import Vertex, Face, CellComplex, Graph
from molior import Molior
import molior.ifc

import tempfile
import logging
from blenderbim.bim import import_ifc
import bpy

bl_info = {
    "name": "Homemaker Topologise",
    "blender": (2, 80, 0),
    "category": "Object",
}


class ObjectTopologise(bpy.types.Operator):
    """Object Topologise"""

    bl_idname = "object.topologise"
    bl_label = "Topologise"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        meshes = []

        for blender_object in context.selected_objects:
            if not blender_object.type == "MESH":
                continue
            # Ignore widgets (if any) for allocating room/space usage
            label = re.match(
                "(bedroom|circulation|circulation_stair|stair|kitchen|living|retail|sahn|toilet)",
                blender_object.name,
                flags=re.IGNORECASE,
            )
            if label:
                continue
            else:
                meshes.append(blender_object)

        # remaining meshes become a single cellcomplex
        faces_ptr = []
        for mesh in meshes:
            vertices = [Vertex.ByCoordinates(*v.co) for v in mesh.data.vertices]

            for polygon in mesh.data.polygons:
                if polygon.area < 0.00001:
                    continue
                stylename = "default"
                if len(mesh.material_slots) > 0:
                    stylename = mesh.material_slots[
                        polygon.material_index
                    ].material.name
                face_ptr = Face.ByVertices([vertices[v] for v in polygon.vertices])
                face_ptr.Set("stylename", stylename)
                faces_ptr.append(face_ptr)
            mesh.hide_viewport = True

        # Generate a Topologic CellComplex
        cc = CellComplex.ByFaces(faces_ptr, 0.0001)
        faces_ptr = []
        cc.Faces(faces_ptr)
        vertices = []
        faces = []
        materials = []
        vertex_id = 0
        for face_ptr in faces_ptr:
            vertices_ptr = []
            face_ptr.VerticesPerimeter(vertices_ptr)
            face = []
            for vertex in vertices_ptr:
                vertices.append([vertex.X(), vertex.Y(), vertex.Z()])
                face.append(vertex_id)
                vertex_id += 1
            faces.append(face)
            materials.append(face_ptr.Get("stylename"))

        new_mesh = bpy.data.meshes.new("faces")
        new_mesh.from_pydata(vertices, [], faces)
        # FIXME reapply materials
        new_mesh.update()
        new_object = bpy.data.objects.new("cellcomplex", new_mesh)
        bpy.data.collections[0].objects.link(new_object)

        return {"FINISHED"}


class ObjectHomemaker(bpy.types.Operator):
    """Object Homemaker Topologise"""

    bl_idname = "object.homemaker"
    bl_label = "Homemaker Topologise"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        meshes = []
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
                centre = [0.0, 0.0, 0.0]
                total = len(blender_object.data.vertices)
                for v in blender_object.data.vertices:
                    coor = v.co[:]
                    centre[0] += coor[0]
                    centre[1] += coor[1]
                    centre[2] += coor[2]
                vertex = Vertex.ByCoordinates(
                    centre[0] / total, centre[1] / total, centre[2] / total
                )
                widgets.append([label[0], vertex])
            else:
                meshes.append(blender_object)

        # Each remaining mesh becomes a separate building
        # FIXME should all end-up in the same IfcProject
        for mesh in meshes:
            vertices = [Vertex.ByCoordinates(*v.co) for v in mesh.data.vertices]
            faces_ptr = []

            for polygon in mesh.data.polygons:
                if polygon.area < 0.00001:
                    continue
                stylename = "default"
                if len(mesh.material_slots) > 0:
                    stylename = mesh.material_slots[
                        polygon.material_index
                    ].material.name
                if stylename == "Material":
                    stylename = "default"
                face_ptr = Face.ByVertices([vertices[v] for v in polygon.vertices])
                face_ptr.Set("stylename", stylename)
                faces_ptr.append(face_ptr)
            mesh.hide_viewport = True

            # Generate a Topologic CellComplex
            cc = CellComplex.ByFaces(faces_ptr, 0.0001)
            # Copy styles from Faces to the CellComplex
            cc.ApplyDictionary(faces_ptr)
            # Assign Cell usages from widgets
            cc.AllocateCells(widgets)
            # Generate a cirulation Graph
            circulation = Graph.Adjacency(cc)
            circulation.Circulation(cc)
            # print(circulation.Dot(cc))

            # Traces are 2D paths that define walls, extrusions and rooms
            # Hulls are 3D shells that define pitched roofs and soffits
            # Collect unique elevations and assign storey numbers
            traces, hulls, normals, elevations = cc.GetTraces()

            # generate an IFC object
            ifc = molior.ifc.init(mesh.name, elevations)

            # TODO enable user defined location for share_dir
            molior_object = Molior(
                file=ifc,
                circulation=circulation,
                elevations=elevations,
                traces=traces,
                hulls=hulls,
                normals=normals,
                cellcomplex=cc,
            )
            molior_object.execute()

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
            bpy.data.collections.get("StructuralItems").hide_viewport = True
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(ObjectTopologise.bl_idname)
    self.layout.operator(ObjectHomemaker.bl_idname)


def register():
    bpy.utils.register_class(ObjectTopologise)
    bpy.utils.register_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ObjectTopologise)
    bpy.utils.unregister_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
