import sys
import os
import re

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append("/home/bruno/src/homemaker-addon")
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/libs/site/packages"))

from topologic import Vertex, Face, CellComplex
from molior import Molior
from molior.ifc import (
    init,
    get_parent_building,
    get_structural_analysis_model_by_name,
    delete_ifc_product,
    purge_unused,
)

import logging
from bonsai.bim import import_ifc
from bonsai.bim.ifc import IfcStore
import bonsai.tool as tool
import bpy
import bmesh

bl_info = {
    "name": "Homemaker Topologise",
    "author": "Bruno Postle",
    "location": "3D Viewport > Object Menu > Homemaker",
    "description": "Design buildings the pointy-clicky way",
    "doc_url": "https://homemaker-addon.readthedocs.io/",
    "blender": (4, 2, 0),
    "support": "COMMUNITY",
    "category": "Object",
}


class addHomemakerPreferences(bpy.types.AddonPreferences):
    bl_idname = "homemaker"

    share_dir: bpy.props.StringProperty(default="share")

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "share_dir")
        row.operator("homemaker.select_share_dir", icon="FILE_FOLDER", text="")


class SelectShareDir(bpy.types.Operator):
    bl_idname = "homemaker.select_share_dir"
    bl_label = "Select Style Directory"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Select the folder containing style definitions..."
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        bpy.context.preferences.addons["homemaker"].preferences.share_dir = (
            os.path.dirname(self.filepath)
        )
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ObjectTopologise(bpy.types.Operator):
    """Object Topologise"""

    bl_idname = "object.topologise"
    bl_label = "Topologise"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ifc_element = tool.Ifc.get_entity(bpy.context.active_object)
        if ifc_element:
            cellcomplex = Molior.get_cellcomplex_from_ifc(ifc_element)
            for new_mesh in meshes_from_cellcomplex(cellcomplex):
                new_object = bpy.data.objects.new(new_mesh.name, new_mesh)
                bpy.context.scene.collection.objects.link(new_object)

            # delete the building containing this element

            self.ifc_building = get_parent_building(ifc_element)
            self.structural_model = get_structural_analysis_model_by_name(
                IfcStore.file, self.ifc_building, self.ifc_building.Name
            )

            for collection in bpy.data.collections:
                if re.match("^IfcBuilding/", collection.name):
                    for myobject in collection.objects:
                        if tool.Ifc.get_entity(myobject) == self.ifc_building:
                            # runs _execute()
                            IfcStore.execute_ifc_operator(self, context)
                            delete_collection(collection)
            bpy.data.orphans_purge(do_recursive=True)

            return {"FINISHED"}

        # FIXME this resets widget origins which looks ugly
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        selected_objects = context.selected_objects
        blender_objects, widgets = process_blender_objects(context.selected_objects)

        # remaining blender_objects become a single cellcomplex
        faces_ptr = []
        for blender_object in blender_objects:
            triangulate_nonplanar(blender_object)
            faces_ptr.extend(topologic_faces_from_blender_object(blender_object))

        # Generate a Topologic CellComplex
        cc = CellComplex.ByFaces(faces_ptr, 0.0001)
        cc.ApplyDictionary(faces_ptr)
        cc.Set("name", blender_objects[0].name)

        for blender_object in selected_objects:
            bpy.data.objects.remove(blender_object)

        for new_mesh in meshes_from_cellcomplex(cc):
            new_object = bpy.data.objects.new(new_mesh.name, new_mesh)
            bpy.context.scene.collection.objects.link(new_object)

        return {"FINISHED"}

    def _execute(self, context):
        delete_ifc_product(IfcStore.file, self.ifc_building)
        delete_ifc_product(IfcStore.file, self.structural_model)
        purge_unused(IfcStore.file)
        # FIXME no idea why this is necessary
        clean_id_map()


class ObjectHomemaker(bpy.types.Operator):
    """Object Homemaker"""

    bl_idname = "object.homemaker"
    bl_label = "Homemaker"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if tool.Ifc.get() is None:
            # creates Project, Units, Representation Contexts etc..
            IfcStore.file = init()

        if "homemaker" in bpy.context.preferences.addons:
            self.share_dir = bpy.context.preferences.addons[
                "homemaker"
            ].preferences.share_dir
        else:
            self.share_dir = "share"

        ifc_element = tool.Ifc.get_entity(bpy.context.active_object)
        if ifc_element:
            self.cellcomplex = Molior.get_cellcomplex_from_ifc(ifc_element)

            if not self.cellcomplex:
                return {"FINISHED"}

            # delete and replace the building containing this element

            self.ifc_building = get_parent_building(ifc_element)
            self.structural_model = get_structural_analysis_model_by_name(
                IfcStore.file, self.ifc_building, self.ifc_building.Name
            )
            self.building_name = self.ifc_building.Name

            for collection in bpy.data.collections:
                if re.match("^IfcBuilding/", collection.name):
                    for myobject in collection.objects:
                        if tool.Ifc.get_entity(myobject) == self.ifc_building:
                            self.action = "regenerate_ifc"
                            IfcStore.execute_ifc_operator(self, context)
        else:
            # FIXME this resets widget origins which looks ugly
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            selected_objects = context.selected_objects
            blender_objects, widgets = process_blender_objects(context.selected_objects)

            # Each remaining blender_object becomes a separate building
            for blender_object in blender_objects:
                triangulate_nonplanar(blender_object)

            self.blender_objects = blender_objects
            self.widgets = widgets

            # runs _execute()
            self.action = "generate_ifc"
            IfcStore.execute_ifc_operator(self, context)

            for blender_object in selected_objects:
                bpy.data.objects.remove(blender_object)

        # delete any IfcProject/* collections, but leave IfcStore intact
        for collection in bpy.data.collections:
            if re.match("^IfcProject/", collection.name):
                delete_collection(collection)
        # delete any Ifc* objects not in IfcProject/ hierarchy
        for obj in bpy.data.objects:
            if re.match("^Ifc", obj.name):
                bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.orphans_purge(do_recursive=True)

        # (re)build blender collections and geometry from IfcStore
        ifc_import_settings = import_ifc.IfcImportSettings.factory(
            bpy.context, "", logging.getLogger("ImportIFC")
        )
        ifc_import_settings.should_setup_viewport_camera = False
        ifc_importer = import_ifc.IfcImporter(ifc_import_settings)
        ifc_importer.execute()
        tool.Project.load_pset_templates()
        tool.Project.load_default_thumbnails()
        tool.Project.set_default_context()
        tool.Project.set_default_modeling_dimensions()

        # Hide Structural objects
        bpy.data.collections.get("IfcStructuralItem").hide_viewport = True
        # Hide stashed CellComplex
        for collection in bpy.data.collections:
            if re.match("^IfcVirtualElement/CellComplex", collection.name):
                collection.hide_viewport = True

        return {"FINISHED"}

    def _execute(self, context):
        if self.action == "regenerate_ifc":
            # remove the old building
            delete_ifc_product(IfcStore.file, self.ifc_building)
            delete_ifc_product(IfcStore.file, self.structural_model)
            purge_unused(IfcStore.file)
            clean_id_map()

            # Molior objects build IFC buildings
            molior_object = Molior.from_cellcomplex(
                file=IfcStore.file,
                cellcomplex=self.cellcomplex,
                name=self.building_name,
                share_dir=self.share_dir,
            )
            molior_object.execute()
        elif self.action == "generate_ifc":
            for blender_object in self.blender_objects:
                # Molior objects build IFC buildings
                molior_object = Molior.from_faces_and_widgets(
                    file=IfcStore.file,
                    faces=topologic_faces_from_blender_object(blender_object),
                    widgets=self.widgets,
                    name=blender_object.name,
                    share_dir=self.share_dir,
                )
                molior_object.execute()


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


def meshes_from_cellcomplex(cc):
    meshes = []
    cells_ptr = []
    cc.Cells(cc, cells_ptr)
    for cell_ptr in cells_ptr:
        centroid = cell_ptr.Centroid()
        cell_usage = cell_ptr.Get("usage")
        if not cell_usage:
            cell_usage = "living"
        new_mesh = bpy.data.meshes.new(cell_usage)
        new_mesh.from_pydata([centroid.Coordinates()], [], [])
        meshes.append(new_mesh)

    faces_ptr = []
    cc.Faces(cc, faces_ptr)
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

    # populate material slots for this new mesh
    for material_name in materials:
        if material_name not in bpy.data.materials:
            bpy.data.materials.new(material_name)
        if material_name not in new_mesh.materials:
            material = bpy.data.materials[material_name]
            new_mesh.materials.append(material)
    # get names/index for each material slot
    lookup = {}
    for index in range(len(new_mesh.materials)):
        lookup[new_mesh.materials[index].name] = index
    # need a bmesh to assign materials
    bm = bmesh.new()
    bm.from_mesh(new_mesh)
    index = 0
    for face in bm.faces:
        face.material_index = lookup[materials[index]]
        index += 1
    bm.to_mesh(new_mesh)
    bm.free()

    new_mesh.update()
    new_mesh_name = cc.Get("name")
    if not new_mesh_name:
        new_mesh_name = "CellComplex"
    new_mesh.name = new_mesh_name
    meshes.append(new_mesh)
    return meshes


def process_blender_objects(selected_objects):
    blender_objects = []
    widgets = []

    for blender_object in selected_objects:
        if not blender_object.type == "MESH":
            continue
        elif re.match("^Ifc", blender_object.name):
            continue
        # Collect widgets (if any) for allocating room/space usage
        label = re.match(
            "(bedroom|circulation|circulation_stair|stair|kitchen|living|outside|retail|sahn|toilet|void)",
            blender_object.name,
            flags=re.IGNORECASE,
        )
        total = len(blender_object.data.vertices)
        if not total:
            continue
        if label:
            centre = [0.0, 0.0, 0.0]
            for v in blender_object.data.vertices:
                coor = v.co[:]
                centre[0] += coor[0]
                centre[1] += coor[1]
                centre[2] += coor[2]
            vertex = Vertex.ByCoordinates(
                centre[0] / total, centre[1] / total, centre[2] / total
            )
            vertex.Set("usage", label[0])
            widgets.append(vertex)
        else:
            blender_objects.append(blender_object)

    return blender_objects, widgets


def delete_collection(blender_collection):
    for obj in blender_collection.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(blender_collection)


def clean_id_map():
    for ifc_definition_id in list(IfcStore.id_map.keys()):
        try:
            IfcStore.file.by_id(ifc_definition_id)
        except RuntimeError:
            del IfcStore.id_map[ifc_definition_id]


def triangulate_nonplanar(blender_object):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = blender_object
    blender_object.select_set(True)
    object_has_nonplanar_material = False
    object_has_other_material = False
    material_slots = blender_object.material_slots
    for material_index in range(len(material_slots)):
        if material_slots[material_index].name == "nonplanar":
            object_has_nonplanar_material = True
        else:
            object_has_other_material = True

    bpy.ops.object.mode_set(mode="EDIT")

    md = bmesh.from_edit_mesh(blender_object.data)
    output = bmesh.ops.connect_verts_nonplanar(md, angle_limit=0.001, faces=md.faces)
    faces = output["faces"]
    if len(faces) > 0:
        bpy.ops.mesh.select_all(action="DESELECT")

        if not object_has_other_material:
            bpy.ops.object.material_slot_add()
            try:
                other_material = bpy.data.materials["default"]
            except KeyError:
                other_material = bpy.data.materials.new(name="default")
            blender_object.active_material = other_material

        if object_has_nonplanar_material:
            blender_object.active_material_index = material_index
        else:
            bpy.ops.object.material_slot_add()
            try:
                nonplanar_material = bpy.data.materials["nonplanar"]
                blender_object.active_material = nonplanar_material
            except KeyError:
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
    bpy.utils.register_class(addHomemakerPreferences)
    bpy.utils.register_class(SelectShareDir)
    bpy.utils.register_class(ObjectTopologise)
    bpy.utils.register_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(addHomemakerPreferences)
    bpy.utils.unregister_class(SelectShareDir)
    bpy.utils.unregister_class(ObjectTopologise)
    bpy.utils.unregister_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
