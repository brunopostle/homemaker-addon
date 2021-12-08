import sys
import os
import re

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append("/home/bruno/src/homemaker-addon")
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/libs/site/packages"))

from topologic import Vertex, Face, CellComplex, Graph
from topologist.helpers import wipe_global_cluster
from molior import Molior
import molior.ifc

import logging
from blenderbim.bim import import_ifc
import blenderbim.bim.ifc
import bpy
import bmesh

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
        # FIXME this resets widget origins which looks ugly
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        blender_objects, widgets = process_blender_objects(context.selected_objects)

        # remaining blender_objects become a single cellcomplex
        faces_ptr = []
        for blender_object in blender_objects:
            triangulate_nonplanar(blender_object)
            faces_ptr.extend(topologic_faces_from_blender_object(blender_object))
            blender_object.hide_viewport = True

        # Generate a Topologic CellComplex
        cc = CellComplex.ByFaces(faces_ptr, 0.0001)
        new_object = bpy.data.objects.new("cellcomplex", mesh_from_cellcomplex(cc))
        bpy.data.collections.items()[0][1].objects.link(new_object)

        return {"FINISHED"}


class ObjectHomemaker(bpy.types.Operator):
    """Object Homemaker Topologise"""

    bl_idname = "object.homemaker"
    bl_label = "Homemaker Topologise"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # FIXME this resets widget origins which looks ugly
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        blender_objects, widgets = process_blender_objects(context.selected_objects)

        # Each remaining blender_object becomes a separate building
        for blender_object in blender_objects:
            triangulate_nonplanar(blender_object)
            faces_ptr = topologic_faces_from_blender_object(blender_object)
            blender_object.hide_viewport = True

            # generate an ifcopenshell model
            ifc = homemaker(faces_ptr, widgets, blender_object.name, "")

            # delete any IfcProject/* collections, but leave IfcStore intact
            have_project = False
            for collection_name in bpy.data.collections.keys():
                project = re.match(
                    "^IfcProject/",
                    collection_name,
                )
                if project:
                    have_project = True
                    delete_collection(bpy.data.collections.get(collection_name))
            if not have_project:
                blenderbim.bim.ifc.IfcStore.purge()
                blenderbim.bim.ifc.IfcStore.file = None

            # merge IfcStore with generated ifcopenshell model
            if blenderbim.bim.ifc.IfcStore.file == None:
                blenderbim.bim.ifc.IfcStore.file = ifc
            else:
                molior.ifc.merge_file(blenderbim.bim.ifc.IfcStore.file, ifc)

            # (re)build blender collections and geometry from IfcStore
            ifc_import_settings = import_ifc.IfcImportSettings.factory(
                bpy.context, "", logging.getLogger("ImportIFC")
            )
            ifc_importer = import_ifc.IfcImporter(ifc_import_settings)
            ifc_importer.execute()

            bpy.data.collections.get("StructuralItems").hide_viewport = True
        return {"FINISHED"}


def homemaker(faces_ptr, widgets, name, user_share_dir):
    wipe_global_cluster([])
    # Generate a Topologic CellComplex
    cc = CellComplex.ByFaces(faces_ptr, 0.0001)
    # Copy styles from Faces to the CellComplex
    cc.ApplyDictionary(faces_ptr)
    wipe_global_cluster([cc])
    # Assign Cell usages from widgets
    cc.AllocateCells(widgets)
    wipe_global_cluster([cc])
    # Generate a circulation Graph
    circulation = Graph.Adjacency(cc)
    circulation.Circulation(cc)
    circulation.Separation(circulation.ShortestPathTable(), cc)

    # print(circulation.Dot(cc))

    # Traces are 2D paths that define walls, extrusions and rooms
    # Hulls are 3D shells that define pitched roofs and soffits
    # Collect unique elevations and assign storey numbers
    traces, hulls, normals, elevations = cc.GetTraces()

    # generate an IFC object
    ifc = molior.ifc.init(name, elevations)

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

    return ifc


def topologic_faces_from_blender_object(blender_object):
    vertices = [Vertex.ByCoordinates(*v.co) for v in blender_object.data.vertices]
    faces_ptr = []

    for polygon in blender_object.data.polygons:
        if polygon.area < 0.00001:
            continue
        stylename = "default"
        if len(blender_object.material_slots) > 0:
            stylename = blender_object.material_slots[
                polygon.material_index
            ].material.name
        if stylename == "Material":
            stylename = "default"
        face_ptr = Face.ByVertices([vertices[v] for v in polygon.vertices])
        face_ptr.Set("stylename", stylename)
        faces_ptr.append(face_ptr)
    return faces_ptr


def mesh_from_cellcomplex(cc):
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
    return new_mesh


def process_blender_objects(selected_objects):
    blender_objects = []
    widgets = []

    for blender_object in selected_objects:
        if not blender_object.type == "MESH":
            continue
        # Collect widgets (if any) for allocating room/space usage
        label = re.match(
            "(bedroom|circulation|circulation_stair|stair|kitchen|living|outside|retail|sahn|toilet)",
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
            blender_objects.append(blender_object)

    return blender_objects, widgets


def delete_collection(blender_collection):
    for obj in blender_collection.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(blender_collection)
    for collection in bpy.data.collections:
        if not collection.users:
            bpy.data.collections.remove(collection)


def triangulate_nonplanar(blender_object):
    object_has_nonplanar_material = False
    material_slots = blender_object.material_slots
    for material_index in range(len(material_slots)):
        if material_slots[material_index].name == "nonplanar":
            object_has_nonplanar_material = True
            break

    bpy.ops.object.mode_set(mode="EDIT")

    md = bmesh.from_edit_mesh(blender_object.data)
    output = bmesh.ops.connect_verts_nonplanar(md, angle_limit=0.001, faces=md.faces)
    faces = output["faces"]
    if len(faces) > 0:
        bpy.ops.mesh.select_all(action="DESELECT")

        if object_has_nonplanar_material:
            blender_object.active_material_index = material_index
        else:
            bpy.ops.object.material_slot_add()
            try:
                nonplanar_material = bpy.data.materials["nonplanar"]
                blender_object.active_material = nonplanar_material
            except:
                nonplanar_material = bpy.data.materials.new(name="nonplanar")
                nonplanar_material.use_nodes = True
                bpy.context.object.active_material = nonplanar_material
                p_node = nonplanar_material.node_tree.nodes.get("Principled BSDF")
                p_node.inputs[0].default_value = [1, 0, 0, 1]

        for face in faces:
            face.select_set(True)
        bpy.ops.object.material_slot_assign()

    bpy.ops.object.mode_set(mode="OBJECT")


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
