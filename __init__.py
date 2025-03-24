import sys
import os
import re
from pathlib import Path
from typing import List, Tuple

if __file__ == "/__init__.py":
    # running in the blender text editor
    sys.path.append(os.path.join(Path.home(), "src", "homemaker-addon"))

from topologic_core import Vertex, Face, CellComplex

# Improved error handling and module imports
try:
    from molior import Molior
    from molior.ifc import (
        init,
        get_parent_building,
        get_structural_analysis_model_by_name,
        delete_ifc_product,
        purge_unused,
    )
except ImportError:
    from .molior import Molior
    from .molior.ifc import (
        init,
        get_parent_building,
        get_structural_analysis_model_by_name,
        delete_ifc_product,
        purge_unused,
    )

from bonsai.bim.ifc import IfcStore
import bonsai.tool as tool
import bpy
import bmesh

# Constants for reuse
EPSILON = 0.0001
DEFAULT_STYLE = "default"
NONPLANAR_STYLE = "nonplanar"
ROOM_TYPES = [
    "bedroom",
    "circulation",
    "circulation_stair",
    "stair",
    "kitchen",
    "living",
    "outside",
    "retail",
    "sahn",
    "toilet",
    "void",
]
ROOM_PATTERN = re.compile("|".join(ROOM_TYPES), flags=re.IGNORECASE)

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


class HomemakerPreferences(bpy.types.AddonPreferences):
    """Addon preferences for Homemaker"""

    if __package__:
        bl_idname = __package__
    else:
        bl_idname = "homemaker"

    if os.path.isabs(__file__):
        share_dir_default = os.path.join(os.path.dirname(__file__), "share")
    else:
        share_dir_default = "share"

    share_dir: bpy.props.StringProperty(
        name="Share Directory",
        description="Directory containing style definitions",
        default=share_dir_default,
        subtype="DIR_PATH",
    )

    def draw(self, context):
        row = self.layout.row()
        row.prop(self, "share_dir")
        row.operator("homemaker.select_share_dir", icon="FILE_FOLDER", text="")


class SelectShareDir(bpy.types.Operator):
    """Select the directory containing style definitions"""

    bl_idname = "homemaker.select_share_dir"
    bl_label = "Select Style Directory"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Select the folder containing style definitions..."
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        if "homemaker" in bpy.context.preferences.addons:
            bpy.context.preferences.addons["homemaker"].preferences.share_dir = (
                os.path.dirname(self.filepath)
            )
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class ObjectTopologise(bpy.types.Operator):
    """Convert objects to topological representation"""

    bl_idname = "object.topologise"
    bl_label = "Topologise"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ifc_element = tool.Ifc.get_entity(bpy.context.active_object)
        if ifc_element:
            return self._handle_ifc_element(context, ifc_element)
        else:
            return self._handle_blender_objects(context)

    def _handle_ifc_element(self, context, ifc_element):
        """Process IFC elements"""
        cellcomplex = Molior.get_cellcomplex_from_ifc(ifc_element)
        if not cellcomplex:
            self.report({"WARNING"}, "Could not get cell complex from IFC element")
            return {"CANCELLED"}

        for new_mesh in meshes_from_cellcomplex(cellcomplex):
            new_object = bpy.data.objects.new(new_mesh.name, new_mesh)
            bpy.context.scene.collection.objects.link(new_object)

        # delete the building containing this element
        self.ifc_building = get_parent_building(ifc_element)
        self.structural_model = get_structural_analysis_model_by_name(
            IfcStore.file, self.ifc_building, self.ifc_building.Name
        )

        IfcStore.execute_ifc_operator(self, context)
        tool.IfcGit.load_project()

        return {"FINISHED"}

    def _handle_blender_objects(self, context):
        """Process regular Blender objects"""
        # Apply transforms (maybe make this optional in the future)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        selected_objects = context.selected_objects
        blender_objects, widgets = process_blender_objects(selected_objects)

        if not blender_objects:
            self.report({"WARNING"}, "No valid objects selected")
            return {"CANCELLED"}

        # Convert objects to faces for topologic processing
        faces_ptr = []
        for blender_object in blender_objects:
            triangulate_nonplanar(blender_object)
            faces_ptr.extend(topologic_faces_from_blender_object(blender_object))

        # Generate a Topologic CellComplex
        cc = CellComplex.ByFaces(faces_ptr, EPSILON)
        cc.ApplyDictionary(faces_ptr)
        cc.Set("name", blender_objects[0].name)

        # Remove original objects
        for blender_object in selected_objects:
            try:
                bpy.data.objects.remove(blender_object)
            except ReferenceError:
                continue

        # Create new meshes from the cell complex
        for new_mesh in meshes_from_cellcomplex(cc):
            new_object = bpy.data.objects.new(new_mesh.name, new_mesh)
            bpy.context.scene.collection.objects.link(new_object)

        return {"FINISHED"}

    def _execute(self, context):
        """Execute IFC operations - called by IfcStore.execute_ifc_operator"""
        delete_ifc_product(IfcStore.file, self.ifc_building)
        delete_ifc_product(IfcStore.file, self.structural_model)
        purge_unused(IfcStore.file)


class ObjectHomemaker(bpy.types.Operator):
    """Convert objects to IFC buildings"""

    bl_idname = "object.homemaker"
    bl_label = "Homemaker"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # Initialize IFC if needed
        if tool.Ifc.get() is None:
            IfcStore.file = init()

        # Get share directory from addon preferences
        self.share_dir = self._get_share_dir()

        ifc_element = tool.Ifc.get_entity(bpy.context.active_object)
        if ifc_element:
            return self._handle_ifc_element(context, ifc_element)
        else:
            return self._handle_blender_objects(context)

    def _get_share_dir(self) -> str:
        """Get the share directory from addon preferences"""
        if "homemaker" in bpy.context.preferences.addons:
            return bpy.context.preferences.addons["homemaker"].preferences.share_dir
        return "share"

    def _handle_ifc_element(self, context, ifc_element):
        """Process IFC elements"""
        self.cellcomplex = Molior.get_cellcomplex_from_ifc(ifc_element)
        if not self.cellcomplex:
            self.report({"WARNING"}, "Could not get cell complex from IFC element")
            return {"CANCELLED"}

        # Delete and replace the building containing this element
        self.ifc_building = get_parent_building(ifc_element)
        self.structural_model = get_structural_analysis_model_by_name(
            IfcStore.file, self.ifc_building, self.ifc_building.Name
        )
        self.building_name = self.ifc_building.Name

        self.action = "regenerate_ifc"
        IfcStore.execute_ifc_operator(self, context)
        tool.IfcGit.load_project()

        # Hide specific collections after processing
        self._hide_specific_collections()

        return {"FINISHED"}

    def _handle_blender_objects(self, context):
        """Process regular Blender objects"""
        # Apply transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        selected_objects = context.selected_objects
        blender_objects, widgets = process_blender_objects(selected_objects)

        if not blender_objects:
            self.report({"WARNING"}, "No valid objects selected")
            return {"CANCELLED"}

        # Prepare objects for IFC conversion
        for blender_object in blender_objects:
            triangulate_nonplanar(blender_object)

        self.blender_objects = blender_objects
        self.widgets = widgets

        self.action = "generate_ifc"
        IfcStore.execute_ifc_operator(self, context)
        tool.IfcGit.load_project()

        # Remove original objects
        for blender_object in selected_objects:
            try:
                bpy.data.objects.remove(blender_object)
            except ReferenceError:
                continue

        # Hide specific collections after processing
        self._hide_specific_collections()

        return {"FINISHED"}

    def _hide_specific_collections(self):
        """Hide structural and cell complex collections"""
        # Hide Structural objects
        structural_collection = bpy.data.collections.get("IfcStructuralItem")
        if structural_collection:
            structural_collection.hide_viewport = True

        # Hide stashed CellComplex
        for collection in bpy.data.collections:
            if re.match("^IfcVirtualElement/CellComplex", collection.name):
                collection.hide_viewport = True

    def _execute(self, context):
        """Execute IFC operations - called by IfcStore.execute_ifc_operator"""
        if self.action == "regenerate_ifc":
            # Remove the old building
            delete_ifc_product(IfcStore.file, self.ifc_building)
            delete_ifc_product(IfcStore.file, self.structural_model)
            purge_unused(IfcStore.file)

            # Create new building from cell complex
            molior_object = Molior.from_cellcomplex(
                file=IfcStore.file,
                cellcomplex=self.cellcomplex,
                name=self.building_name,
                share_dir=self.share_dir,
            )
            molior_object.execute()

        elif self.action == "generate_ifc":
            # Create new buildings from blender objects
            for blender_object in self.blender_objects:
                molior_object = Molior.from_faces_and_widgets(
                    file=IfcStore.file,
                    faces=topologic_faces_from_blender_object(blender_object),
                    widgets=self.widgets,
                    name=blender_object.name,
                    share_dir=self.share_dir,
                )
                molior_object.execute()


def topologic_faces_from_blender_object(blender_object) -> List[Face]:
    """Convert a Blender object to Topologic faces"""
    vertices = [Vertex.ByCoordinates(*v.co) for v in blender_object.data.vertices]
    faces_ptr = []

    for polygon in blender_object.data.polygons:
        if polygon.area < EPSILON:
            continue

        # Get style name from material slot
        stylename = DEFAULT_STYLE
        if len(blender_object.material_slots) > 0:
            material = blender_object.material_slots[polygon.material_index].material
            if material and material.name != "Material":
                stylename = material.name

        # Create topologic face
        face_ptr = Face.ByVertices([vertices[v] for v in polygon.vertices])
        face_ptr.Set("stylename", stylename)
        faces_ptr.append(face_ptr)

    return faces_ptr


def meshes_from_cellcomplex(cc) -> List[bpy.types.Mesh]:
    """Create Blender meshes from a Topologic cell complex"""
    meshes = []

    # Create mesh for cell centroids
    cells_ptr = []
    cc.Cells(cc, cells_ptr)
    for cell_ptr in cells_ptr:
        centroid = cell_ptr.Centroid()
        cell_usage = cell_ptr.Get("usage") or "living"
        new_mesh = bpy.data.meshes.new(cell_usage)
        new_mesh.from_pydata([centroid.Coordinates()], [], [])
        meshes.append(new_mesh)

    # Create mesh for all faces in the cell complex
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
        materials.append(face_ptr.Get("stylename") or DEFAULT_STYLE)

    new_mesh = bpy.data.meshes.new("faces")
    new_mesh.from_pydata(vertices, [], faces)

    # Set up materials
    _setup_materials(new_mesh, materials)

    # Finalize mesh
    new_mesh.update()
    new_mesh_name = cc.Get("name") or "CellComplex"
    new_mesh.name = new_mesh_name
    meshes.append(new_mesh)

    return meshes


def _setup_materials(mesh, material_names):
    """Set up materials for a mesh"""
    # Create materials if they don't exist
    for material_name in material_names:
        if material_name not in bpy.data.materials:
            bpy.data.materials.new(material_name)
        if material_name not in mesh.materials:
            material = bpy.data.materials[material_name]
            mesh.materials.append(material)

    # Map material names to indices
    material_index_map = {mesh.materials[i].name: i for i in range(len(mesh.materials))}

    # Assign materials to faces
    bm = bmesh.new()
    bm.from_mesh(mesh)

    for i, face in enumerate(bm.faces):
        face.material_index = material_index_map.get(material_names[i], 0)

    # Remove doubles and update mesh
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=EPSILON)
    bm.to_mesh(mesh)
    bm.free()


def process_blender_objects(selected_objects) -> Tuple[List, List]:
    """Process selected Blender objects, separating regular objects and 'widgets'"""
    blender_objects = []
    widgets = []

    for blender_object in selected_objects:
        # Skip non-mesh objects and IFC objects
        if not blender_object.type == "MESH" or re.match("^Ifc", blender_object.name):
            continue

        # Check if there are any vertices
        if not blender_object.data.vertices:
            continue

        # Check if this is a room type widget
        label_match = ROOM_PATTERN.match(blender_object.name)
        if label_match:
            # Calculate centroid
            centroid = _calculate_centroid(blender_object)
            vertex = Vertex.ByCoordinates(*centroid)
            vertex.Set("usage", label_match[0])
            widgets.append(vertex)
        else:
            blender_objects.append(blender_object)

    return blender_objects, widgets


def _calculate_centroid(obj) -> List[float]:
    """Calculate the centroid of a mesh object"""
    total = len(obj.data.vertices)
    centre = [0.0, 0.0, 0.0]

    for v in obj.data.vertices:
        coor = v.co[:]
        centre[0] += coor[0]
        centre[1] += coor[1]
        centre[2] += coor[2]

    return [centre[0] / total, centre[1] / total, centre[2] / total]


def triangulate_nonplanar(blender_object):
    """Triangulate non-planar faces and assign a special material to them"""
    # Select only this object
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = blender_object
    blender_object.select_set(True)

    # Check material slots
    object_has_nonplanar_material = False
    object_has_other_material = False
    material_slots = blender_object.material_slots

    for material_index in range(len(material_slots)):
        if material_slots[material_index].name == NONPLANAR_STYLE:
            object_has_nonplanar_material = True
        else:
            object_has_other_material = True

    # Enter edit mode
    bpy.ops.object.mode_set(mode="EDIT")
    md = bmesh.from_edit_mesh(blender_object.data)

    # Connect non-planar vertices
    output = bmesh.ops.connect_verts_nonplanar(md, angle_limit=0.001, faces=md.faces)
    faces = output["faces"]

    if faces:
        bpy.ops.mesh.select_all(action="DESELECT")

        # Add default material if needed
        if not object_has_other_material:
            bpy.ops.object.material_slot_add()
            try:
                other_material = bpy.data.materials[DEFAULT_STYLE]
            except KeyError:
                other_material = bpy.data.materials.new(name=DEFAULT_STYLE)
            blender_object.active_material = other_material

        # Add or select nonplanar material
        if object_has_nonplanar_material:
            for i, slot in enumerate(blender_object.material_slots):
                if slot.name == NONPLANAR_STYLE:
                    blender_object.active_material_index = i
                    break
        else:
            bpy.ops.object.material_slot_add()
            try:
                nonplanar_material = bpy.data.materials[NONPLANAR_STYLE]
                blender_object.active_material = nonplanar_material
            except KeyError:
                # Create new nonplanar material with red color
                nonplanar_material = bpy.data.materials.new(name=NONPLANAR_STYLE)
                nonplanar_material.use_nodes = True
                blender_object.active_material = nonplanar_material
                p_node = nonplanar_material.node_tree.nodes.get("Principled BSDF")
                if p_node:
                    p_node.inputs[0].default_value = [1, 0, 0, 1]

        # Select and assign material to non-planar faces
        for face in faces:
            face.select_set(True)
        bpy.ops.object.material_slot_assign()

    # Return to object mode
    bpy.ops.object.mode_set(mode="OBJECT")


def menu_func(self, context):
    """Add operators to the Object menu"""
    self.layout.operator(ObjectTopologise.bl_idname)
    self.layout.operator(ObjectHomemaker.bl_idname)


def register():
    """Register the addon"""
    bpy.utils.register_class(HomemakerPreferences)
    bpy.utils.register_class(SelectShareDir)
    bpy.utils.register_class(ObjectTopologise)
    bpy.utils.register_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    """Unregister the addon"""
    bpy.utils.unregister_class(HomemakerPreferences)
    bpy.utils.unregister_class(SelectShareDir)
    bpy.utils.unregister_class(ObjectTopologise)
    bpy.utils.unregister_class(ObjectHomemaker)
    bpy.types.VIEW3D_MT_object.remove(menu_func)


if __name__ == "__main__":
    register()
