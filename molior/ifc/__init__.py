""" Domain-specific extensions to IfcOpenShell

A collection of code for commonly used IFC related tasks

"""

import os
import ezdxf
import ifcopenshell.api
from molior.geometry import (
    matrix_align,
    add_2d,
    subtract_2d,
    x_product_3d,
    subtract_3d,
    normalise_3d,
)

run = ifcopenshell.api.run


def init(name="Homemaker Project"):
    """Creates and sets up an ifc 'file' object"""
    file = run("project.create_file")

    run("owner.add_person", file)
    run("owner.add_organisation", file)

    run(
        "root.create_entity",
        file,
        ifc_class="IfcProject",
        name=name,
    )

    run("unit.assign_unit", file, length={"is_metric": True, "raw": "METERS"})

    parent_context = run("context.add_context", file, context_type="Model")
    run(
        "context.add_context",
        file,
        context_identifier="Body",
        context_type=parent_context.ContextType,
        parent=parent_context,
        target_view="MODEL_VIEW",
    )
    run(
        "context.add_context",
        file,
        context_identifier="Reference",
        context_type=parent_context.ContextType,
        parent=parent_context,
        target_view="GRAPH_VIEW",
    )
    run(
        "context.add_context",
        file,
        context_identifier="Axis",
        context_type=parent_context.ContextType,
        parent=parent_context,
        target_view="GRAPH_VIEW",
    )

    return file


def create_site(self, project, site_name):
    """Add a Site to a Project"""
    site = run("root.create_entity", self, ifc_class="IfcSite", name=site_name)
    run("aggregate.assign_object", self, product=site, relating_object=project)
    return site


def create_building(self, site, building_name):
    """Add a Building to a Site"""
    building = run(
        "root.create_entity", self, ifc_class="IfcBuilding", name=building_name
    )
    run("aggregate.assign_object", self, product=building, relating_object=site)
    return building


def create_structural_analysis_model(self, building, model_name):
    """Add a structural model to a building"""
    model = run("structural.add_structural_analysis_model", self)
    model.Name = "Structure/" + model_name
    rel = run(
        "root.create_entity",
        self,
        ifc_class="IfcRelServicesBuildings",
        name=model.Name,
    )
    rel.RelatingSystem = model
    rel.RelatedBuildings = [building]
    return model


def create_storeys(self, building, elevations):
    """Add Storey Spatial Elements to a Building, given a dictionary of elevations/name"""
    if elevations == {}:
        elevations[0.0] = 0
    for elevation in sorted(elevations):
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
        run("aggregate.assign_object", self, product=mystorey, relating_object=building)
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


def assign_extrusion_fromDXF(
    self, subcontext, element, directrix, stylename, path_dxf, transform
):
    """Create an extrusion given a directrix and DXF profile filepath"""
    identifier = stylename + "/" + os.path.splitext(os.path.split(path_dxf)[-1])[0]

    # let's see if there is an existing MaterialProfileSet recorded
    materialprofilesets = {}
    for materialprofileset in self.by_type("IfcMaterialProfileSet"):
        materialprofilesets[materialprofileset.Name] = materialprofileset

    if identifier in materialprofilesets:
        # profile(s) already defined, use them
        closedprofiledefs = [
            materialprofile.Profile
            for materialprofile in materialprofilesets[identifier].MaterialProfiles
        ]
    else:
        # profile(s) not defined, load from the DXF
        doc = ezdxf.readfile(path_dxf)
        model = doc.modelspace()
        closedprofiledefs = []
        profile_index = 0
        for entity in model:
            if entity.get_mode() == "AcDb2dPolyline":
                profile = list(entity.points())
                if not profile[-1] == profile[0]:
                    # a closed polyline has first and last points coincident
                    profile.append(profile[0])
                closedprofiledefs.append(
                    self.createIfcArbitraryClosedProfileDef(
                        "AREA",
                        identifier + "_" + str(profile_index),
                        self.createIfcPolyline(
                            [
                                self.createIfcCartesianPoint([point[1], point[0]])
                                for point in profile
                            ]
                        ),
                    ),
                )
                profile_index += 1
        # record profile(s) in a MaterialProfileSet so we can find them again
        self.createIfcMaterialProfileSet(
            identifier,
            None,
            [
                self.createIfcMaterialProfile(None, None, None, profiledef)
                for profiledef in closedprofiledefs
            ],
        )

    # define these outside the loop as they are the same for each profile
    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )
    polyline = self.createIfcPolyline(
        [self.createIfcCartesianPoint(point) for point in directrix]
    )
    plane = self.createIfcPlane(axis)

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


def create_tessellations_from_dxf(self, path_dxf):
    """Create Tessellations given a DXF filepath"""
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
    tessellations = []
    for entity in model:
        if entity.get_mode() == "AcDbPolyFaceMesh":
            if entity.faces():
                vertices, faces = entity.indexed_faces()
                tessellations.append(
                    create_tessellation_from_mesh(
                        self,
                        [vertex.dxf.location for vertex in vertices],
                        [face.indices for face in faces],
                    )
                )
    return tessellations


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
        if get_building(storey) == building:
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


def assign_space_byindex(self, entity, building, index):
    """Assign object to a Space by index"""
    spaces = {}
    for space in self.by_type("IfcSpace"):
        if get_building(space) == building:
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


def assign_representation_fromDXF(self, subcontext, element, stylename, path_dxf):
    """Assign geometry from DXF unless a TypeProduct with this name already exists"""
    product_type = get_type_by_dxf(
        self, subcontext, element.is_a() + "Type", stylename, path_dxf
    )
    run(
        "type.assign_type",
        self,
        related_object=element,
        relating_type=product_type,
    )


def get_type_by_dxf(self, subcontext, ifc_type, stylename, path_dxf):
    """Fetch a TypeProduct from DXF geometry unless a TypeProduct with this name already exists"""
    identifier = stylename + "/" + os.path.splitext(os.path.split(path_dxf)[-1])[0]

    # let's see if there is an existing Type Product defined in the relevant library
    for library in self.by_type("IfcProjectLibrary"):
        if library.Name == stylename:
            for declares in library.Declares:
                for definition in declares.RelatedDefinitions:
                    if definition.is_a(ifc_type) and definition.Name == identifier:
                        return definition
    # otherwise, load a DXF polyface mesh as a Tessellation
    brep = self.createIfcShapeRepresentation(
        subcontext,
        subcontext.ContextIdentifier,
        "Tessellation",
        create_tessellations_from_dxf(self, path_dxf),
    )
    type_product = run(
        "root.create_entity",
        self,
        ifc_class=ifc_type,
        name=identifier,
    )
    run(
        "project.assign_declaration",
        self,
        definition=type_product,
        relating_context=get_library_by_name(self, stylename),
    )
    if type_product.is_a("IfcDoorType"):
        type_product.PredefinedType = "DOOR"
        type_product.OperationType = "SINGLE_SWING_LEFT"
    elif type_product.is_a("IfcWindowType"):
        type_product.PredefinedType = "WINDOW"
        type_product.PartitioningType = "SINGLE_PANEL"
    elif type_product.is_a("IfcColumnType"):
        type_product.PredefinedType = "COLUMN"
    elif type_product.is_a("IfcRailingType"):
        type_product.PredefinedType = "BALUSTRADE"
    else:
        type_product.PredefinedType = "USERDEFINED"
    run(
        "geometry.assign_representation",
        self,
        product=type_product,
        representation=brep,
    )
    return type_product


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


def get_building(entity):
    """Retrieve whatever Building contains this entity, or None"""
    if entity.is_a("IfcElement"):
        parents = entity.ContainedInStructure
        if not parents:
            return None
        parent = parents[0].RelatingStructure
    elif entity.is_a("IfcSpatialElement") or entity.is_a("IfcStructuralItem"):
        decomposes = entity.Decomposes
        if not decomposes:
            return None
        parent = decomposes[0].RelatingObject
    elif entity.is_a("IfcSystem"):
        services = entity.ServicesBuildings
        if not services:
            return None
        parent = services[0].RelatedBuildings[0]
    else:
        return None
    if parent.is_a("IfcBuilding"):
        return parent
    return get_building(parent)


def get_material_by_name(self, subcontext, material_name, style_materials):
    """Retrieve an IfcMaterial by name, creating it if necessary"""
    materials = {}
    for material in self.by_type("IfcMaterial"):
        materials[material.Name] = material
    if material_name in materials:
        mymaterial = materials[material_name]
    else:
        # we need to create a new material
        mymaterial = run("material.add_material", self, name=material_name)
        params = {
            "surface_colour": [0.9, 0.9, 0.9],
            "diffuse_colour": [1.0, 1.0, 1.0],
            "transparency": 0.0,
            "external_definition": None,
        }
        if material_name in style_materials:
            params.update(style_materials[material_name])
            if "psets" in style_materials[material_name]:
                for name, properties in style_materials[material_name]["psets"].items():
                    pset = run("pset.add_pset", self, product=mymaterial, name=name)
                    run(
                        "pset.edit_pset",
                        self,
                        pset=pset,
                        properties=properties,
                    )
        style = run("style.add_style", self, name=material_name)
        run(
            "style.add_surface_style",
            self,
            style=style,
            attributes={
                "SurfaceColour": {
                    "Name": None,
                    "Red": params["surface_colour"][0],
                    "Green": params["surface_colour"][1],
                    "Blue": params["surface_colour"][2],
                },
                "DiffuseColour": {
                    "Name": None,
                    "Red": params["diffuse_colour"][0],
                    "Green": params["diffuse_colour"][1],
                    "Blue": params["diffuse_colour"][2],
                },
                "Transparency": params["transparency"],
                "ReflectanceMethod": "PLASTIC",
            },
        )
        run(
            "style.assign_material_style",
            self,
            material=mymaterial,
            style=style,
            context=subcontext,
        )
    return mymaterial
