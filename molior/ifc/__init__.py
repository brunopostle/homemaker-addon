""" Domain-specific extensions to IfcOpenShell

A collection of code for commonly used IFC related tasks

"""

from typing import Dict, List, Union, Optional, Any
import weakref
import numpy as np
import ifcopenshell
import ifcopenshell.entity_instance
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.owner
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.structural
import ifcopenshell.api.style
import ifcopenshell.api.unit
import ifcopenshell.util.system
from ..geometry import (
    matrix_align,
    add_2d,
    subtract_2d,
    x_product_3d,
    subtract_3d,
    normalise_3d,
)

api = ifcopenshell.api

# Registry to keep library files alive as long as the project file exists
# Maps project IFC files to lists of library IFC files they depend on
_library_file_registry: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _register_library_file(
    project_file: ifcopenshell.file, library_file: ifcopenshell.file
) -> None:
    """Register a library file to keep it alive as long as the project file exists.

    This prevents library files from being garbage collected while their entities
    are still referenced by the project file, which would cause segmentation faults.

    Args:
        project_file: The IFC project file that depends on the library.
        library_file: The IFC library file to keep alive.
    """
    if project_file not in _library_file_registry:
        _library_file_registry[project_file] = []
    if library_file not in _library_file_registry[project_file]:
        _library_file_registry[project_file].append(library_file)


def init(
    name: str = "Homemaker Project", file: Optional[ifcopenshell.file] = None
) -> ifcopenshell.file:
    """Creates and sets up an IFC 'file' object with basic project structure.

    Args:
        name: The name to give to the IFC project.
        file: An existing IFC file to use. If None, creates a new file.

    Returns:
        The initialized IFC file with project, person, organization, and units.
    """
    if file is None:
        file = api.project.create_file()
    # TODO skip each of these if already existing
    api.owner.add_person(file)
    api.owner.add_organisation(file)

    api.root.create_entity(
        file,
        ifc_class="IfcProject",
        name=name,
    )

    length_unit = api.unit.add_si_unit(file, unit_type="LENGTHUNIT")
    force_unit = api.unit.add_si_unit(file, unit_type="FORCEUNIT", prefix="KILO")
    unit_assignment = api.unit.assign_unit(file)
    unit_assignment.Units = [
        length_unit,
        api.unit.add_si_unit(file, unit_type="AREAUNIT"),
        api.unit.add_si_unit(file, unit_type="VOLUMEUNIT"),
        api.unit.add_si_unit(file, unit_type="PLANEANGLEUNIT"),
        force_unit,
        api.unit.add_derived_unit(
            file, "LINEARMOMENTUNIT", None, {force_unit: 1, length_unit: 1}
        ),
        api.unit.add_derived_unit(
            file, "LINEARFORCEUNIT", None, {force_unit: 1, length_unit: -1}
        ),
        api.unit.add_derived_unit(
            file, "PLANARFORCEUNIT", None, {force_unit: 1, length_unit: -2}
        ),
    ]

    create_default_contexts(file)

    return file


def create_default_contexts(self: ifcopenshell.file) -> None:
    """Creates a standard set of representation contexts for the IFC model.

    This function establishes a comprehensive set of geometric representation contexts
    for different views and purposes within the IFC model.

    Args:
        self: The IFC file where contexts should be created.
    """
    get_context_by_name(
        self,
        context_identifier="Body",
        parent_context_identifier="Model",
        target_view="MODEL_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Box",
        parent_context_identifier="Model",
        target_view="MODEL_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Clearance",
        parent_context_identifier="Model",
        target_view="MODEL_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Surface",
        parent_context_identifier="Model",
        target_view="SKETCH_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Reference",
        parent_context_identifier="Model",
        target_view="GRAPH_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="FootPrint",
        parent_context_identifier="Model",
        target_view="PLAN_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Reference",
        parent_context_identifier="Model",
        target_view="SKETCH_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Annotation",
        parent_context_identifier="Plan",
        target_view="PLAN_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Annotation",
        parent_context_identifier="Plan",
        target_view="SECTION_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Annotation",
        parent_context_identifier="Plan",
        target_view="ELEVATION_VIEW",
    )
    get_context_by_name(
        self,
        context_identifier="Axis",
        parent_context_identifier="Model",
        target_view="GRAPH_VIEW",
    )


def create_storeys(
    self: ifcopenshell.file,
    parent: ifcopenshell.entity_instance,
    elevations: Dict[float, int],
) -> None:
    """Add Storey Spatial Elements to a Building.

    Args:
        self: The IFC file.
        parent: The parent building element to which storeys will be added.
        elevations: A dictionary mapping elevation heights (float) to storey numbers (int).
            For example: {0.0: 0, 3.5: 1, 7.0: 2} for ground, first, and second floors.
    """
    if elevations == {}:
        elevations[0.0] = 0
    for elevation in sorted(elevations):
        for storey in self.by_type("IfcBuildingStorey"):
            if (
                storey.Name == str(elevations[elevation])
                and storey.Decomposes
                and storey.Decomposes[0].RelatingObject == parent
            ):
                continue
        mystorey = api.root.create_entity(
            self,
            ifc_class="IfcBuildingStorey",
            name=str(elevations[elevation]),
        )
        mystorey.Elevation = elevation
        mystorey.Description = "Storey " + mystorey.Name
        mystorey.LongName = mystorey.Description
        mystorey.CompositionType = "ELEMENT"
        api.aggregate.assign_object(self, products=[mystorey], relating_object=parent)
        api.geometry.edit_object_placement(
            self,
            product=mystorey,
            matrix=matrix_align([0.0, 0.0, elevation], [1.0, 0.0, 0.0]),
        )


def get_context_by_name(
    self: ifcopenshell.file,
    parent_context_identifier: Optional[str] = None,
    context_identifier: Optional[str] = None,
    target_view: Optional[str] = None,
) -> ifcopenshell.entity_instance:
    """Retrieve or create a Representation Context in the IFC model.

    This function locates an existing context or creates a new one based on the
    provided parameters.

    Args:
        self: The IFC file where the context should be found or created.
        parent_context_identifier: The identifier of the parent context (e.g., "Model" or "Plan").
        context_identifier: The identifier of the context to retrieve or create (e.g., "Body", "Axis").
        target_view: The target view for the context (e.g., "MODEL_VIEW", "PLAN_VIEW").

    Returns:
        The retrieved or newly created context entity.
    """
    mycontext = get_context(
        self,
        parent_context_identifier,
        subcontext=context_identifier,
        target_view=target_view,
    )
    if mycontext:
        return mycontext
    if context_identifier in ["Model", "Plan", "NotDefined"]:
        mycontext = get_context(self, context_identifier)
        if mycontext:
            return mycontext
        return api.context.add_context(self, context_type=context_identifier)
    parent_context = get_context_by_name(
        self, context_identifier=parent_context_identifier
    )
    return api.context.add_context(
        self,
        context_identifier=context_identifier,
        context_type=parent_context.ContextType,
        parent=parent_context,
        target_view=target_view,
    )


# pasted from ifcopenshell.util.representation due to blender dependency
def get_context(
    ifc_file: ifcopenshell.file,
    context: Optional[str] = None,
    subcontext: Optional[str] = None,
    target_view: Optional[str] = None,
) -> Optional[ifcopenshell.entity_instance]:
    """Retrieve a geometric representation context from the IFC file.

    Args:
        ifc_file: The IFC file to search in.
        context: The top-level context type (e.g., "Model", "Plan").
        subcontext: The subcontext identifier (e.g., "Body", "Axis").
        target_view: The target view (e.g., "MODEL_VIEW", "PLAN_VIEW").

    Returns:
        The matching context entity, or None if not found.
    """
    if subcontext or target_view:
        elements = ifc_file.by_type("IfcGeometricRepresentationSubContext")
    else:
        elements = ifc_file.by_type(
            "IfcGeometricRepresentationContext", include_subtypes=False
        )
    for element in elements:
        if context and element.ContextType != context:
            continue
        if subcontext and getattr(element, "ContextIdentifier") != subcontext:
            continue
        if target_view and getattr(element, "TargetView") != target_view:
            continue
        return element
    return None


def get_site_by_name(
    self: ifcopenshell.file, parent: ifcopenshell.entity_instance, name: str
) -> ifcopenshell.entity_instance:
    """Add a Site to a Project, or retrieve if already there.

    Args:
        self: The IFC file.
        parent: The parent project to which the site belongs.
        name: The name of the site to find or create.

    Returns:
        The existing or newly created site entity.
    """
    for site in self.by_type("IfcSite"):
        if (
            site.Name == name
            and site.Decomposes
            and site.Decomposes[0].RelatingObject == parent
        ):
            return site
    site = api.root.create_entity(self, ifc_class="IfcSite", name=name)
    # TODO allow setting location
    site.RefLatitude = [53, 23, 0]
    site.RefLongitude = [1, 28, 0]
    site.RefElevation = 75.0
    api.aggregate.assign_object(self, products=[site], relating_object=parent)
    return site


def get_building_by_name(
    self: ifcopenshell.file, parent: ifcopenshell.entity_instance, name: str
) -> ifcopenshell.entity_instance:
    """Add a Building to a Site, or retrieve if already there.

    Args:
        self: The IFC file.
        parent: The parent site to which the building belongs.
        name: The name of the building to find or create.

    Returns:
        The existing or newly created building entity.
    """
    for building in self.by_type("IfcBuilding"):
        if (
            building.Name == name
            and building.Decomposes
            and building.Decomposes[0].RelatingObject == parent
        ):
            return building
    building = api.root.create_entity(self, ifc_class="IfcBuilding", name=name)
    api.geometry.edit_object_placement(
        self,
        product=building,
    )
    api.aggregate.assign_object(self, products=[building], relating_object=parent)
    return building


def get_structural_analysis_model_by_name(
    self: ifcopenshell.file, spatial_element: ifcopenshell.entity_instance, name: str
) -> ifcopenshell.entity_instance:
    """Add a structural model to a building, or retrieve if already there.

    Args:
        self: The IFC file.
        spatial_element: The building or other spatial element the structural model services.
        name: The name for the structural model.

    Returns:
        The existing or newly created structural analysis model entity.
    """
    for model in self.by_type("IfcStructuralAnalysisModel"):
        if (
            model.Name == "Structure/" + name
            and model.ServicesBuildings
            and spatial_element in model.ServicesBuildings[0].RelatedBuildings
        ):
            return model
    model = api.structural.add_structural_analysis_model(self)
    model.Name = "Structure/" + name
    rel = api.root.create_entity(
        self,
        ifc_class="IfcRelServicesBuildings",
        name=model.Name,
    )
    rel.RelatingSystem = model
    rel.RelatedBuildings = [spatial_element]
    load_group = api.root.create_entity(
        self,
        ifc_class="IfcStructuralLoadGroup",
        name="Load Group",
        predefined_type="NOTDEFINED",
    )
    load_group.ActionSource = "NOTDEFINED"
    load_group.ActionType = "NOTDEFINED"
    model.LoadedBy = [load_group]
    return model


def get_library_by_name(
    self: ifcopenshell.file, library_name: str
) -> ifcopenshell.entity_instance:
    """Retrieve a Project Library by name, creating it if necessary.

    Args:
        self: The IFC file.
        library_name: The name of the library to find or create.

    Returns:
        The existing or newly created project library entity.
    """
    for library in self.by_type("IfcProjectLibrary"):
        if library.Name == library_name:
            return library
    library = api.root.create_entity(
        self, ifc_class="IfcProjectLibrary", name=library_name
    )
    api.project.assign_declaration(
        self,
        definitions=[library],
        relating_context=self.by_type("IfcProject")[0],
    )
    return library


def get_material_by_name(
    self: ifcopenshell.file,
    style_object: Any,
    stylename: str = "default",
    name: str = "Error",
) -> ifcopenshell.entity_instance:
    """Retrieve an IfcMaterial by name, creating it if necessary.

    Args:
        self: The IFC file.
        style_object: The style manager object that provides library access.
        stylename: The name of the style collection to search in.
        name: The name of the material to find or create.

    Returns:
        The existing or newly created material entity.
    """
    materials = {}
    for material in self.by_type("IfcMaterial"):
        materials[material.Name] = material
    if name in materials:
        mymaterial = materials[name]
    else:
        (found_stylename, library_file, element) = style_object.get_from_library(
            stylename, "IfcMaterial", name
        )
        if element:
            # Register library file to prevent garbage collection
            _register_library_file(self, library_file)
            # add to current project from library file
            mymaterial = api.project.append_asset(
                self, library=library_file, element=element
            )
        else:
            # we need to create a new material
            mymaterial = api.material.add_material(self, name=name)
    return mymaterial


def get_parent_building(
    entity: ifcopenshell.entity_instance,
) -> Optional[ifcopenshell.entity_instance]:
    """Retrieve whatever Building contains this entity, or None.

    This function traverses the IFC relationship hierarchy to find the building
    that contains the given entity.

    Args:
        entity: The IFC entity to find the containing building for.

    Returns:
        The parent building entity, or None if not found.
    """
    if entity.is_a("IfcElement"):
        parents = entity.ContainedInStructure
        decomposes = entity.Decomposes
        if not parents:
            if not decomposes:
                return None
            parent = decomposes[0].RelatingObject
        else:
            parent = parents[0].RelatingStructure
    elif entity.is_a("IfcSpatialElement") or entity.is_a("IfcSpatialStructureElement"):
        decomposes = entity.Decomposes
        if not decomposes:
            return None
        parent = decomposes[0].RelatingObject
    elif entity.is_a("IfcStructuralItem"):
        assignments = entity.HasAssignments
        if not assignments:
            return None
        parent = assignments[0].RelatingGroup
    elif entity.is_a("IfcSystem"):
        services = entity.ServicesBuildings
        if not services:
            return None
        parent = services[0].RelatedBuildings[0]
    else:
        return None
    if parent.is_a("IfcBuilding"):
        return parent
    return get_parent_building(parent)


def get_thickness(
    self: ifcopenshell.file, product: ifcopenshell.entity_instance
) -> float:
    """Gets total thickness for extruded products and types.

    For products with associated material layer sets, calculates the
    total thickness by summing the thicknesses of all layers.

    Args:
        self: The IFC file.
        product: The product to calculate thickness for.

    Returns:
        The total thickness as a float.
    """
    thickness = 0.0
    for association in product.HasAssociations:
        if association.is_a("IfcRelAssociatesMaterial"):
            relating_material = association.RelatingMaterial
            if relating_material.is_a("IfcMaterialLayerSet"):
                for material_layer in relating_material.MaterialLayers:
                    thickness += material_layer.LayerThickness
    return thickness


def create_closed_profile_from_points(
    self: ifcopenshell.file, points: List[List[float]]
) -> ifcopenshell.entity_instance:
    """Creates a closed 2D profile from list of 2D points.

    Args:
        self: The IFC file.
        points: A list of 2D points as [x, y] coordinates that define the profile outline.
            The first and last points should match to create a closed loop.

    Returns:
        An IfcArbitraryClosedProfileDef entity.
    """
    # a closed polyline has first and last points coincident
    if not points[len(points) - 1] == points[0]:
        points.append(points[0])

    return self.createIfcArbitraryClosedProfileDef(
        "AREA",
        None,
        self.createIfcPolyline(
            [self.createIfcCartesianPoint(point) for point in points]
        ),
    )


def create_extruded_area_solid(
    self: ifcopenshell.file,
    points: List[List[float]],
    height: float,
    direction: List[float] = [0.0, 0.0, 1.0],
) -> ifcopenshell.entity_instance:
    """A simple vertically extruded profile.

    Args:
        self: The IFC file.
        points: A list of 2D points defining the profile to extrude.
        height: The extrusion height.
        direction: The direction vector for extrusion (default: upward in Z-axis).

    Returns:
        An IfcExtrudedAreaSolid entity.
    """
    return self.createIfcExtrudedAreaSolid(
        create_closed_profile_from_points(self, points),
        self.createIfcAxis2Placement3D(
            self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        ),
        self.createIfcDirection(direction),
        height,
    )


def create_extruded_area_solid2(
    self: ifcopenshell.file,
    material_profile: ifcopenshell.entity_instance,
    start: List[float],
    direction: List[float],
    length: float,
) -> ifcopenshell.entity_instance:
    """Create an extruded solid from a material profile, with specific orientation.

    Args:
        self: The IFC file.
        material_profile: The material profile containing the profile to extrude.
        start: The starting point [x, y, z] for the extrusion.
        direction: The direction vector for the extrusion axis.
        length: The length of extrusion.

    Returns:
        An IfcExtrudedAreaSolid entity.
    """
    return self.createIfcExtrudedAreaSolid(
        material_profile.Profile,
        self.createIfcAxis2Placement3D(
            self.createIfcCartesianPoint(start),
            self.createIfcDirection(subtract_3d([0.0, 0.0, 0.0], direction)),
            self.createIfcDirection([direction[1], -direction[0], direction[2]]),
        ),
        self.createIfcDirection([0.0, 0.0, -1.0]),
        length,
    )


def create_curve_bounded_plane(
    self: ifcopenshell.file, polygon: List[List[float]], matrix: np.ndarray
) -> ifcopenshell.entity_instance:
    """Create a bounded shape in the Z=0 plane.

    Args:
        self: The IFC file.
        polygon: A list of 2D points defining the boundary curve.
        matrix: A transformation matrix defining the position and orientation of the plane.

    Returns:
        An IfcCurveBoundedPlane entity.
    """
    if not polygon[-1] == polygon[0]:
        polygon.append(polygon[0])

    return self.createIfcCurveBoundedPlane(
        self.createIfcPlane(
            self.createIfcAxis2Placement3D(
                self.createIfcCartesianPoint(matrix[:, 3][0:3].tolist()),
                self.createIfcDirection(matrix[:, 2][0:3].tolist()),
                self.createIfcDirection(matrix[:, 0][0:3].tolist()),
            )
        ),
        self.createIfcPolyline(
            [self.createIfcCartesianPoint(point) for point in polygon]
        ),
        [],
    )


def create_face_surface(
    self: ifcopenshell.file, polygon: List[List[float]], normal: List[float]
) -> ifcopenshell.entity_instance:
    """Create a single-face shape.

    Args:
        self: The IFC file.
        polygon: A list of 3D points defining the vertices of the face.
        normal: The normal vector of the face.

    Returns:
        An IfcFaceSurface entity.
    """
    surface = self.createIfcPlane(
        self.createIfcAxis2Placement3D(
            self.createIfcCartesianPoint(polygon[0]),
            self.createIfcDirection(normal),
            self.createIfcDirection(normalise_3d(subtract_3d(polygon[1], polygon[0]))),
        )
    )
    vertices = []
    for point in polygon:
        vertices.append(self.createIfcVertexPoint(self.createIfcCartesianPoint(point)))

    face_bound = self.createIfcFaceBound(
        self.createIfcEdgeLoop(
            [
                self.createIfcOrientedEdge(None, None, edge, True)
                for edge in [
                    self.createIfcEdge(vertices[i - 1], vertices[i])
                    for i in range(len(polygon))
                ]
            ]
        ),
        True,
    )
    return self.createIfcFaceSurface([face_bound], surface, True)


def create_tessellation_from_mesh(
    self: ifcopenshell.file, vertices: List[List[float]], faces: List[List[int]]
) -> ifcopenshell.entity_instance:
    """Create a Tessellation from vertex coordinates and faces.

    Args:
        self: The IFC file.
        vertices: A list of 3D points defining the vertices of the mesh.
        faces: A list of lists of vertex indices defining the faces of the mesh.

    Returns:
        An IfcPolygonalFaceSet entity.
    """
    pointlist = self.createIfcCartesianPointList3D(vertices)
    indexedfaces = [
        self.createIfcIndexedPolygonalFace([index + 1 for index in face])
        for face in faces
    ]
    return self.createIfcPolygonalFaceSet(pointlist, True, indexedfaces, None)


def create_tessellations_from_mesh_split(
    self: ifcopenshell.file,
    vertices: List[List[float]],
    faces: Dict[str, List[List[int]]],
) -> List[ifcopenshell.entity_instance]:
    """Create a Tessellation from vertex coordinates and split faces.

    Args:
        self: The IFC file.
        vertices: A list of 3D points defining the vertices of the mesh.
        faces: A dictionary mapping style names to lists of face vertex indices.

    Returns:
        A list of IfcPolygonalFaceSet entities with associated styles.
    """
    pointlist = self.createIfcCartesianPointList3D(vertices)
    tessellations = []
    index = 0
    for stylename in faces:
        indexedfaces = [
            self.createIfcIndexedPolygonalFace([index + 1 for index in face])
            for face in faces[stylename]
        ]
        tessellation = self.createIfcPolygonalFaceSet(
            pointlist, False, indexedfaces, None
        )
        tessellations.append(tessellation)
        style = api.style.add_style(self, name=stylename)
        fac = (index % 5) / 5
        api.style.add_surface_style(
            self,
            style=style,
            ifc_class="IfcSurfaceStyleShading",
            attributes={
                "SurfaceColour": {
                    "Name": stylename,
                    "Red": fac,
                    "Green": 1.0 - fac,
                    "Blue": 0.0,
                },
                "Transparency": 0.8,
            },
        )
        self.createIfcStyledItem(tessellation, [style], stylename)
        index += 1
    return tessellations


def clip_solid(
    self: ifcopenshell.file,
    solid: ifcopenshell.entity_instance,
    start: List[float],
    end: List[float],
) -> ifcopenshell.entity_instance:
    """Clip a wall using a half-space solid.

    Args:
        self: The IFC file.
        solid: The solid to be clipped.
        start: The start point of the clipping plane.
        end: The end point of the clipping plane.

    Returns:
        An IfcBooleanClippingResult entity.
    """
    vector = subtract_3d(end, start)
    perp_plan = normalise_3d([0 - vector[1], vector[0], 0.0])
    xprod = x_product_3d(vector, perp_plan)

    polygon = [
        add_2d(start[0:2], perp_plan[0:2]),
        add_2d(end[0:2], perp_plan[0:2]),
        subtract_2d(end[0:2], perp_plan[0:2]),
        subtract_2d(start[0:2], perp_plan[0:2]),
        add_2d(start[0:2], perp_plan[0:2]),
    ]

    return self.createIfcBooleanClippingResult(
        "DIFFERENCE",
        solid,
        self.createIfcPolygonalBoundedHalfSpace(
            self.createIfcPlane(
                self.createIfcAxis2Placement3D(
                    self.createIfcCartesianPoint(start),
                    self.createIfcDirection(xprod),
                    self.createIfcDirection(perp_plan),
                )
            ),
            False,
            self.createIfcAxis2Placement3D(
                self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
            ),
            self.createIfcPolyline(
                [self.createIfcCartesianPoint(point) for point in polygon]
            ),
        ),
    )


def add_pset(
    self: ifcopenshell.file,
    product: ifcopenshell.entity_instance,
    name: str,
    properties: Dict[str, Any],
) -> None:
    """Helper method to add an Ifc PropertySet.

    Args:
        self: The IFC file.
        product: The product to add the property set to.
        name: The name of the property set.
        properties: A dictionary of property names and values.
    """
    pset = api.pset.add_pset(self, product=product, name=name)
    api.pset.edit_pset(
        self,
        pset=pset,
        properties=properties,
    )


def add_face_topology_epsets(
    self: ifcopenshell.file,
    entity: ifcopenshell.entity_instance,
    face: Optional[Any],
    back_cell: Optional[Any],
    front_cell: Optional[Any],
) -> None:
    """Add topology-related property sets to a face-based entity.

    Args:
        self: The IFC file.
        entity: The entity to add properties to.
        face: The topological face, which may have properties like index and style.
        back_cell: The cell behind the face.
        front_cell: The cell in front of the face.
    """
    if face:
        face_index = face.Get("index")
        if face_index is not None:
            add_pset(self, entity, "EPset_Topology", {"FaceIndex": str(face_index)})
        face_stylename = face.Get("stylename")
        if face_stylename is not None:
            add_pset(self, entity, "EPset_Topology", {"StyleName": str(face_stylename)})
    if front_cell:
        front_cell_index = front_cell.Get("index")
        if front_cell_index is not None:
            add_pset(
                self,
                entity,
                "EPset_Topology",
                {"FrontCellIndex": str(front_cell_index)},
            )
    if back_cell:
        back_cell_index = back_cell.Get("index")
        if back_cell_index is not None:
            add_pset(
                self,
                entity,
                "EPset_Topology",
                {"BackCellIndex": str(back_cell_index)},
            )


def add_cell_topology_epsets(
    self: ifcopenshell.file, entity: ifcopenshell.entity_instance, cell: Optional[Any]
) -> None:
    """Add topology-related property sets to a cell-based entity.

    Args:
        self: The IFC file.
        entity: The entity to add properties to.
        cell: The topological cell, which may have properties like index and usage.
    """
    if cell:
        cell_index = cell.Get("index")
        if cell_index is not None:
            add_pset(self, entity, "EPset_Topology", {"CellIndex": cell_index})
        cell_usage = cell.Get("usage")
        if cell_usage is not None:
            add_pset(self, entity, "EPset_Topology", {"Usage": cell_usage})


def assign_storey_byindex(
    self: ifcopenshell.file,
    entity: ifcopenshell.entity_instance,
    building: ifcopenshell.entity_instance,
    index: Union[int, str],
) -> ifcopenshell.entity_instance:
    """Assign object to a storey by index.

    Args:
        self: The IFC file.
        entity: The entity to assign to a storey.
        building: The building containing the storeys.
        index: The index or name of the storey to assign to.

    Returns:
        The storey that the entity was assigned to.
    """
    storeys = {}
    for storey in self.by_type("IfcBuildingStorey"):
        if get_parent_building(storey) == building:
            storeys[storey.Name] = storey
    if entity.is_a("IfcSpatialElement"):
        api.aggregate.assign_object(
            self,
            products=[entity],
            relating_object=storeys[str(index)],
        )
    else:
        api.spatial.assign_container(
            self,
            products=[entity],
            relating_structure=storeys[str(index)],
        )
    return storeys[str(index)]


def assign_space_byindex(
    self: ifcopenshell.file,
    entity: ifcopenshell.entity_instance,
    building: ifcopenshell.entity_instance,
    index: Union[int, str],
) -> None:
    """Assign object to a Space by index.

    Args:
        self: The IFC file.
        entity: The entity to assign to a space.
        building: The building containing the spaces.
        index: The index of the space to assign to, matching the CellIndex in EPset_Topology.
    """
    spaces = {}
    for space in self.by_type("IfcSpace"):
        if get_parent_building(space) == building:
            pset_topology = ifcopenshell.util.element.get_psets(space).get(
                "EPset_Topology"
            )
            if pset_topology:
                spaces[pset_topology["CellIndex"]] = space
    if str(index) not in spaces:
        return
    if entity.is_a("IfcSpatialElement"):
        api.aggregate.assign_object(
            self,
            products=[entity],
            relating_object=spaces[str(index)],
        )
    else:
        api.spatial.assign_container(
            self,
            products=[entity],
            relating_structure=spaces[str(index)],
        )


def get_type_object(
    self: ifcopenshell.file,
    style_object: Any,
    ifc_type: str = "IfcBuildingElementProxyType",
    stylename: str = "default",
    name: str = "error",
) -> ifcopenshell.entity_instance:
    """Fetch a Type Object locally, or from an external IFC library.

    Args:
        self: The IFC file.
        style_object: The style manager object that provides library access.
        ifc_type: The IFC class type to create or retrieve.
        stylename: The name of the style collection to search in.
        name: The name of the type object to find or create.

    Returns:
        The existing or newly created type object entity.
    """
    # let's see if there is an existing Type Product defined in the relevant library
    library = get_library_by_name(self, stylename)
    for declares in library.Declares:
        for definition in declares.RelatedDefinitions:
            if definition.is_a(ifc_type) and definition.Name == name:
                return definition
    # otherwise, load from IFC library file
    (found_stylename, library_file, element) = style_object.get_from_library(
        stylename, ifc_type, name
    )
    if element:
        # Register library file to prevent garbage collection
        _register_library_file(self, library_file)
        # add to current project from library file
        definition = api.project.append_asset(
            self, library=library_file, element=element
        )
    else:
        definition = api.root.create_entity(
            self,
            ifc_class=ifc_type,
            name=name,
        )
    # add to internal library
    api.project.assign_declaration(
        self,
        definitions=[definition],
        relating_context=get_library_by_name(self, stylename),
    )
    return definition


def delete_ifc_product(
    self: ifcopenshell.file, product: Optional[ifcopenshell.entity_instance]
) -> None:
    """Recursively delete a product and its children.

    This function traverses the relationships of the product to find and delete
    all related objects, ensuring clean removal without orphaned references.

    Args:
        self: The IFC file.
        product: The product to delete, or None (in which case no action is taken).
    """
    if not product:
        return
    if getattr(product, "IsDecomposedBy", None):
        for child in product.IsDecomposedBy:
            for child_object in child.RelatedObjects:
                delete_ifc_product(self, child_object)
    if getattr(product, "IsGroupedBy", None):
        for child in product.IsGroupedBy:
            for child_object in child.RelatedObjects:
                delete_ifc_product(self, child_object)
    if getattr(product, "Nests", None):
        for child in product.Nests:
            for child_product in child.RelatedObjects:
                delete_ifc_product(self, child_product)
    if product.is_a("IfcSpatialElement"):
        for child in product.ContainsElements:
            for child_product in child.RelatedElements:
                delete_ifc_product(self, child_product)
    if getattr(product, "FillsVoids", None):
        api.feature.remove_filling(self, element=product)
    if product.is_a("IfcOpeningElement"):
        if product.HasFillings:
            for rel in product.HasFillings:
                api.feature.remove_filling(self, element=rel.RelatedBuildingElement)
        else:
            if product.VoidsElements:
                api.feature.remove_filling(self, element=product)
    else:
        if getattr(product, "HasOpenings", None):
            for rel in product.HasOpenings:
                api.feature.remove_filling(self, element=rel.RelatedOpeningElement)
        for port in ifcopenshell.util.system.get_ports(product):
            api.root.remove_product(self, product=port)
    api.root.remove_product(self, product=product)


def purge_unused(self: ifcopenshell.file) -> None:
    """Delete unused entities from the IFC file.

    This function identifies and removes various types of unused entities
    that might remain in the model after other operations, such as property sets
    without references, placements without objects, etc.

    Args:
        self: The IFC file to clean up.
    """
    todo = True
    while todo:
        todo = False
        for pset in self.by_type("IfcPropertySet"):
            if (
                not pset.DefinesType
                and not pset.IsDefinedBy
                and not pset.DefinesOccurrence
            ):
                delete_ifc_product(self, pset)
                todo = True
        for rep in self.by_type("IfcMaterialDefinitionRepresentation"):
            if not rep.RepresentedMaterial:
                api.root.remove_product(self, product=rep)
                todo = True
        for ext in self.by_type("IfcExtendedProperties"):
            if not ext.Properties:
                api.root.remove_product(self, product=ext)
                todo = True
        for placement in self.by_type("IfcLocalPlacement"):
            if not placement.PlacesObject and not placement.ReferencedByPlacements:
                rel = placement.RelativePlacement
                self.remove(rel.Location)
                self.remove(rel.RefDirection)
                if getattr(rel, "Axis", None):
                    self.remove(rel.Axis)
                self.remove(rel)
                self.remove(placement)
                todo = True
        for entity in self.by_type("IfcConnectionGeometry"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcBoundaryCondition"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcPresentationItem"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcPresentationStyle"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcProfileDef"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcRepresentation"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcGeometricRepresentationItem"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True
        for entity in self.by_type("IfcMaterialDefinition"):
            if not self.get_inverse(entity):
                self.remove(entity)
                todo = True

        # these are clearing up invalid results of root.remove_product
        for rel in self.by_type("IfcRelConnectsStructuralMember"):
            if not rel.RelatingStructuralMember:
                self.remove(rel)
                todo = True
        for rel in self.by_type("IfcRelAssignsToProduct"):
            if not rel.RelatingProduct and not self.get_inverse(rel):
                self.remove(rel)
                todo = True
        for rel in self.by_type("IfcRelServicesBuildings"):
            if not rel.RelatingSystem:
                self.remove(rel)
                todo = True
        for rel in self.by_type("IfcRelAssignsToGroup"):
            if not rel.RelatingGroup:
                self.remove(rel)
                todo = True
        for rel in self.by_type("IfcRelDeclares"):
            if not rel.RelatedDefinitions and not self.get_inverse(rel):
                self.remove(rel)
                todo = True
