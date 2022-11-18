""" Domain-specific extensions to IfcOpenShell

A collection of code for commonly used IFC related tasks

"""

import ifcopenshell.api
import ifcopenshell.util.representation
from molior.geometry import (
    matrix_align,
    add_2d,
    subtract_2d,
    x_product_3d,
    subtract_3d,
    normalise_3d,
)

run = ifcopenshell.api.run


def init(name="Homemaker Project", file=None):
    """Creates and sets up an ifc 'file' object"""
    if file == None:
        file = run("project.create_file")
    # TODO skip each of these if already existing
    run("owner.add_person", file)
    run("owner.add_organisation", file)

    run(
        "root.create_entity",
        file,
        ifc_class="IfcProject",
        name=name,
    )

    unit_assignment = run(
        "unit.assign_unit", file, length={"is_metric": True, "raw": "METERS"}
    )
    unit_assignment.Units = [
        *unit_assignment.Units,
        run("unit.add_si_unit", file, name="RADIAN", unit_type="PLANEANGLEUNIT"),
    ]

    create_default_contexts(file)

    return file


def create_default_contexts(self):
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
        parent_context_identifier="Plan",
        target_view="GRAPH_VIEW",
    )


def get_context_by_name(
    self,
    parent_context_identifier=None,
    context_identifier=None,
    target_view=None,
):
    """Retrieve or create a Representation Context"""
    mycontext = ifcopenshell.util.representation.get_context(
        self,
        parent_context_identifier,
        subcontext=context_identifier,
        target_view=target_view,
    )
    if mycontext:
        return mycontext
    if context_identifier in ["Model", "Plan", "NotDefined"]:
        mycontext = ifcopenshell.util.representation.get_context(
            self, context_identifier
        )
        if mycontext:
            return mycontext
        return run("context.add_context", self, context_type=context_identifier)
    parent_context = get_context_by_name(
        self, context_identifier=parent_context_identifier
    )
    return run(
        "context.add_context",
        self,
        context_identifier=context_identifier,
        context_type=parent_context.ContextType,
        parent=parent_context,
        target_view=target_view,
    )


def get_site_by_name(self, parent, name):
    """Add a Site to a Project, or retrieve if already there"""
    for site in self.by_type("IfcSite"):
        if (
            site.Name == name
            and site.Decomposes
            and site.Decomposes[0].RelatingObject == parent
        ):
            return site
    site = run("root.create_entity", self, ifc_class="IfcSite", name=name)
    # TODO allow setting location
    site.RefLatitude = [53, 23, 0]
    site.RefLongitude = [1, 28, 0]
    site.RefElevation = 75.0
    run("aggregate.assign_object", self, product=site, relating_object=parent)
    return site


def get_building_by_name(self, parent, name):
    """Add a Building to a Site, or retrieve if already there"""
    for building in self.by_type("IfcBuilding"):
        if (
            building.Name == name
            and building.Decomposes
            and building.Decomposes[0].RelatingObject == parent
        ):
            return building
    building = run("root.create_entity", self, ifc_class="IfcBuilding", name=name)
    run("aggregate.assign_object", self, product=building, relating_object=parent)
    return building


def get_structural_analysis_model_by_name(self, spatial_element, name):
    """Add a structural model to a building, or retrieve if already there"""
    for model in self.by_type("IfcStructuralAnalysisModel"):
        if (
            model.Name == "Structure/" + name
            and model.ServicesBuildings
            and spatial_element in model.ServicesBuildings[0].RelatedBuildings
        ):
            return model
    model = run("structural.add_structural_analysis_model", self)
    model.Name = "Structure/" + name
    rel = run(
        "root.create_entity",
        self,
        ifc_class="IfcRelServicesBuildings",
        name=model.Name,
    )
    rel.RelatingSystem = model
    rel.RelatedBuildings = [spatial_element]
    return model


def create_storeys(self, parent, elevations):
    """Add Storey Spatial Elements to a Building, given a dictionary of elevations/name"""
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
        mystorey = run(
            "root.create_entity",
            self,
            ifc_class="IfcBuildingStorey",
            name=str(elevations[elevation]),
        )
        mystorey.Elevation = elevation
        mystorey.Description = "Storey " + mystorey.Name
        mystorey.LongName = mystorey.Description
        mystorey.CompositionType = "ELEMENT"
        run("aggregate.assign_object", self, product=mystorey, relating_object=parent)
        run(
            "geometry.edit_object_placement",
            self,
            product=mystorey,
            matrix=matrix_align([0.0, 0.0, elevation], [1.0, 0.0, 0.0]),
        )


def create_extruded_area_solid(self, profile, height, direction=[0.0, 0.0, 1.0]):
    """A simple vertically extruded profile"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last points coincident
        profile.append(profile[0])

    return self.createIfcExtrudedAreaSolid(
        self.createIfcArbitraryClosedProfileDef(
            "AREA",
            None,
            self.createIfcPolyline(
                [self.createIfcCartesianPoint(point) for point in profile]
            ),
        ),
        self.createIfcAxis2Placement3D(
            self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
        ),
        self.createIfcDirection(direction),
        height,
    )


def clip_solid(self, solid, start, end):
    """Clip a wall using a half-space solid"""
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
                    None,
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


def create_curve_bounded_plane(self, polygon, matrix):
    """Create a bounded shape in the Z=0 plane"""
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


def create_face_surface(self, polygon, normal):
    """Create a single-face shape"""
    surface = self.createIfcPlane(
        self.createIfcAxis2Placement3D(
            self.createIfcCartesianPoint(polygon[0]),
            self.createIfcDirection(normal),
            self.createIfcDirection(normalise_3d(subtract_3d(polygon[1], polygon[0]))),
        )
    )
    face_bound = self.createIfcFaceBound(
        self.createIfcEdgeLoop(
            [
                self.createIfcOrientedEdge(None, None, edge, True)
                for edge in [
                    self.createIfcEdge(
                        self.createIfcVertexPoint(
                            self.createIfcCartesianPoint(polygon[i - 1])
                        ),
                        self.createIfcVertexPoint(
                            self.createIfcCartesianPoint(polygon[i])
                        ),
                    )
                    for i in range(len(polygon))
                ]
            ]
        ),
        True,
    )
    return self.createIfcFaceSurface([face_bound], surface, True)


def assign_extrusion(
    self,
    style_object=None,
    context_identifier="Body",
    element=None,
    directrix=[[0.0, 0.0], [0.0, 1.0]],
    stylename="default",
    name="My Extruded Type",
    transform=None,
):
    """Create an extrusion given a directrix"""
    ifc_type = element.is_a() + "Type"

    type_product = get_type_object(
        self,
        style_object,
        ifc_type=ifc_type,
        stylename=stylename,
        name=name,
    )

    run(
        "type.assign_type",
        self,
        related_object=element,
        relating_type=type_product,
    )

    subcontext = get_context_by_name(self, context_identifier=context_identifier)

    # define these outside the loop as they are the same for each profile
    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )
    polyline = self.createIfcPolyline(
        [self.createIfcCartesianPoint(point) for point in directrix]
    )
    plane = self.createIfcPlane(axis)

    # TODO create chain of Extruded Area Solids with clipped ends
    closedprofiledefs = []
    for association in type_product.HasAssociations:
        if association.is_a(
            "IfcRelAssociatesMaterial"
        ) and association.RelatingMaterial.is_a("IfcMaterialProfileSet"):
            materialprofileset = association.RelatingMaterial
            closedprofiledefs = [
                materialprofile.Profile
                for materialprofile in materialprofileset.MaterialProfiles
            ]
    run(
        "geometry.assign_representation",
        self,
        product=element,
        representation=self.createIfcShapeRepresentation(
            subcontext,
            subcontext.ContextIdentifier,
            "AdvancedSweptSolid",
            [
                self.createIfcSurfaceCurveSweptAreaSolid(
                    self.createIfcDerivedProfileDef(
                        "AREA",
                        None,
                        closedprofiledef,
                        transform,
                        None,
                    ),
                    axis,
                    polyline,
                    0.0,
                    1.0,
                    plane,
                )
                for closedprofiledef in closedprofiledefs
            ],
        ),
    )


def create_tessellation_from_mesh(self, vertices, faces):
    """Create a Tessellation from vertex coordinates and faces"""
    pointlist = self.createIfcCartesianPointList3D(vertices)
    indexedfaces = [
        self.createIfcIndexedPolygonalFace([index + 1 for index in face])
        for face in faces
    ]
    return self.createIfcPolygonalFaceSet(pointlist, None, indexedfaces, None)


def assign_storey_byindex(self, entity, building, index):
    """Assign object to a storey by index"""
    storeys = {}
    for storey in self.by_type("IfcBuildingStorey"):
        if get_parent_building(storey) == building:
            storeys[storey.Name] = storey
    if entity.is_a("IfcSpatialElement"):
        run(
            "aggregate.assign_object",
            self,
            product=entity,
            relating_object=storeys[str(index)],
        )
    else:
        run(
            "spatial.assign_container",
            self,
            product=entity,
            relating_structure=storeys[str(index)],
        )
    return storeys[str(index)]


def assign_space_byindex(self, entity, building, index):
    """Assign object to a Space by index"""
    spaces = {}
    for space in self.by_type("IfcSpace"):
        if get_parent_building(space) == building:
            pset_topology = ifcopenshell.util.element.get_psets(space).get(
                "EPset_Topology"
            )
            if pset_topology:
                spaces[pset_topology["CellIndex"]] = space
    if not str(index) in spaces:
        return
    if entity.is_a("IfcSpatialElement"):
        run(
            "aggregate.assign_object",
            self,
            product=entity,
            relating_object=spaces[str(index)],
        )
    else:
        run(
            "spatial.assign_container",
            self,
            product=entity,
            relating_structure=spaces[str(index)],
        )


def add_pset(self, product, name, properties):
    """Helper method to add an Ifc Pset"""
    pset = run("pset.add_pset", self, product=product, name=name)
    run(
        "pset.edit_pset",
        self,
        pset=pset,
        properties=properties,
    )


def add_face_topology_epsets(self, entity, face, back_cell, front_cell):
    if face:
        face_index = face.Get("index")
        if not face_index == None:
            add_pset(self, entity, "EPset_Topology", {"FaceIndex": str(face_index)})
        face_stylename = face.Get("stylename")
        if not face_stylename == None:
            add_pset(self, entity, "EPset_Topology", {"StyleName": str(face_stylename)})
    if front_cell:
        front_cell_index = front_cell.Get("index")
        if not front_cell_index == None:
            add_pset(
                self,
                entity,
                "EPset_Topology",
                {"FrontCellIndex": str(front_cell_index)},
            )
    if back_cell:
        back_cell_index = back_cell.Get("index")
        if not back_cell_index == None:
            add_pset(
                self,
                entity,
                "EPset_Topology",
                {"BackCellIndex": str(back_cell_index)},
            )


def add_topologic_epsets(self, entity, topology):
    add_pset(self, entity, "EPset_Topologic_Dictionary", topology.DumpDictionary())


def add_cell_topology_epsets(self, entity, cell):
    if cell:
        cell_index = cell.Get("index")
        if cell_index != None:
            add_pset(self, entity, "EPset_Topology", {"CellIndex": cell_index})
        cell_usage = cell.Get("usage")
        if cell_usage != None:
            add_pset(self, entity, "EPset_Topology", {"Usage": cell_usage})


def assign_type_by_name(
    self,
    style_object,
    element=None,
    stylename="default",
    name="error",
):
    """Assign Type from an internal or external IFC library"""
    type_product = get_type_object(
        self,
        style_object,
        ifc_type=element.is_a() + "Type",
        stylename=stylename,
        name=name,
    )
    run(
        "type.assign_type",
        self,
        related_object=element,
        relating_type=type_product,
    )
    return type_product


def get_type_object(
    self,
    style_object,
    ifc_type="IfcBuildingElementProxyType",
    stylename="default",
    name="error",
):
    """Fetch a Type Object locally, or from an external IFC library"""
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
        # add to current project from library file
        definition = run(
            "project.append_asset", self, library=library_file, element=element
        )
    else:
        definition = run(
            "root.create_entity",
            self,
            ifc_class=ifc_type,
            name=name,
        )
    # add to internal library
    run(
        "project.assign_declaration",
        self,
        definition=definition,
        relating_context=get_library_by_name(self, stylename),
    )
    return definition


def get_library_by_name(self, library_name):
    """Retrieve a Project Library by name, creating it if necessary"""
    for library in self.by_type("IfcProjectLibrary"):
        if library.Name == library_name:
            return library
    library = run(
        "root.create_entity", self, ifc_class="IfcProjectLibrary", name=library_name
    )
    run(
        "project.assign_declaration",
        self,
        definition=library,
        relating_context=self.by_type("IfcProject")[0],
    )
    return library


def get_parent_building(entity):
    """Retrieve whatever Building contains this entity, or None"""
    if entity.is_a("IfcElement"):
        parents = entity.ContainedInStructure
        decomposes = entity.Decomposes
        if not parents:
            if not decomposes:
                return None
            parent = decomposes[0].RelatingObject
        else:
            parent = parents[0].RelatingStructure
    elif entity.is_a("IfcSpatialElement"):
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


def get_material_by_name(self, style_object, stylename="default", name="Error"):
    """Retrieve an IfcMaterial by name, creating it if necessary"""
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
            # add to current project from library file
            mymaterial = run(
                "project.append_asset", self, library=library_file, element=element
            )
        else:
            # we need to create a new material
            mymaterial = run("material.add_material", self, name=name)
    return mymaterial


def get_extruded_type_by_name(
    self,
    context_identifier="Body",
    ifc_type="IfcColumnType",
    name="My Cheesy Column",
    stylename="default",
    style_object=None,
    profiles=[
        {
            "ifc_class": "IfcRectangleProfileDef",
            "material": "Cheese",
            "parameters": {"ProfileType": "AREA", "XDim": 0.1, "YDim": 0.2},
            "position": {"Location": [0.0, 0.0], "RefDirection": [1.0, 0.0]},
        }
    ],
):
    """Retrieve an extruded type, creating if necessary"""
    identifier = name
    library = get_library_by_name(self, stylename)

    # use an existing Type if defined in this library
    for declares in library.Declares:
        for definition in declares.RelatedDefinitions:
            if definition.is_a(ifc_type) and definition.Name == identifier:
                return definition

    # create the Type
    type_product = run("root.create_entity", self, ifc_class=ifc_type, name=name)
    run(
        "project.assign_declaration",
        self,
        definition=type_product,
        relating_context=library,
    )
    if hasattr(type_product, "PredefinedType"):
        type_product.PredefinedType = "USERDEFINED"
    # this type is going have a Material Profile Set
    profile_set = run(
        "material.assign_material",
        self,
        product=type_product,
        type="IfcMaterialProfileSet",
    ).RelatingMaterial

    for profile in profiles:
        # add an item to this Material Profile Set
        material_profile = run(
            "material.add_profile",
            self,
            profile_set=profile_set,
            material=get_material_by_name(
                self,
                style_object,
                name=profile["material"],
                stylename=stylename,
            ),
        )
        # create a Parameterized Profile
        parameterized_profile = run(
            "profile.add_parameterized_profile", self, ifc_class=profile["ifc_class"]
        )
        if "position" in profile:
            position = profile["position"]
            parameterized_profile.Position = self.createIfcAxis2Placement2D(
                self.createIfcCartesianPoint(position["Location"]),
                self.createIfcDirection(position["RefDirection"]),
            )
        run(
            "profile.edit_profile",
            self,
            profile=parameterized_profile,
            attributes=profile["parameters"],
        )
        # add our Parameterized Profile to this item
        run(
            "material.assign_profile",
            self,
            material_profile=material_profile,
            profile=parameterized_profile,
        )

    return type_product
