from ifcopenshell.file import file as ifcfile
import ezdxf
import os
import ifcopenshell.api
from molior.geometry_2d import matrix_align

run = ifcopenshell.api.run


def init(building_name, elevations):
    ifc = run("project.create_file")

    run("owner.add_person", ifc)
    run("owner.add_organisation", ifc)

    project = run(
        "root.create_entity",
        ifc,
        ifc_class="IfcProject",
        name="My Project",
    )

    run("unit.assign_unit", ifc, length={"is_metric": True, "raw": "METERS"})

    # TODO should create Plan, Footprint etc. contexts here
    run("context.add_context", ifc)
    run(
        "context.add_context",
        ifc,
        context="Model",
        subcontext="Body",
        target_view="MODEL_VIEW",
    )

    # create and relate site and building
    site = run("root.create_entity", ifc, ifc_class="IfcSite", name="My Site")
    run("aggregate.assign_object", ifc, product=site, relating_object=project)
    building = run(
        "root.create_entity", ifc, ifc_class="IfcBuilding", name=building_name
    )
    run("aggregate.assign_object", ifc, product=building, relating_object=site)
    for elevation in sorted(elevations):
        mystorey = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name=str(elevations[elevation]),
        )
        run("aggregate.assign_object", ifc, product=mystorey, relating_object=building)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=mystorey,
            matrix=matrix_align([0.0, 0.0, elevation], [1.0, 0.0, 0.0]),
        )
    return ifc


def createCurve2D(self, context, profile):
    """A simple centreline"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last profile coincident
        profile.append(profile[0])

    return self.createIfcShapeRepresentation(
        context,
        "Axis",
        "Curve2D",
        [
            self.createIfcPolyline(
                [self.createIfcCartesianPoint(point) for point in profile]
            )
        ],
    )


def createSweptSolid(self, context, profile, height):
    """A simple vertically extruded profile"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last points coincident
        profile.append(profile[0])

    return self.createIfcShapeRepresentation(
        context,
        "Body",
        "SweptSolid",
        [
            self.createIfcExtrudedAreaSolid(
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
                self.createIfcDirection([0.0, 0.0, 1.0]),
                height,
            )
        ],
    )


def createAdvancedSweptSolid(self, context, profile, directrix):
    """A simple horizontally extruded profile following a directrix path"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last points coincident
        profile.append(profile[0])

    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )

    return self.createIfcShapeRepresentation(
        context,
        "Body",
        "AdvancedSweptSolid",
        [
            self.createIfcSurfaceCurveSweptAreaSolid(
                self.createIfcArbitraryClosedProfileDef(
                    "AREA",
                    None,
                    self.createIfcPolyline(
                        [self.createIfcCartesianPoint(point) for point in profile]
                    ),
                ),
                axis,
                self.createIfcPolyline(
                    [self.createIfcCartesianPoint(point) for point in directrix]
                ),
                0.0,
                1.0,
                self.createIfcPlane(axis),
            )
        ],
    )


def assign_extrusion_fromDXF(
    self, bodycontext, element, directrix, stylename, path_dxf
):
    identifier = stylename + "/" + os.path.split(path_dxf)[-1]

    # let's see if there is an existing ExternalReference recorded
    externalreferences = {}
    for externalreference in self.by_type("IfcExternalReferenceRelationship"):
        externalreferences[externalreference.Name] = externalreference

    if identifier in externalreferences:
        # profile(s) already defined, use them
        closedprofiledefs = externalreferences[identifier].RelatedResourceObjects
    else:
        # profile(s) not defined, load from the DXF
        doc = ezdxf.readfile(path_dxf)
        model = doc.modelspace()
        closedprofiledefs = []
        for entity in model:
            if entity.get_mode() == "AcDb2dPolyline":
                profile = list(entity.points())
                if not profile[-1] == profile[0]:
                    # a closed polyline has first and last points coincident
                    profile.append(profile[0])
                closedprofiledefs.append(
                    self.createIfcArbitraryClosedProfileDef(
                        "AREA",
                        None,
                        self.createIfcPolyline(
                            [
                                self.createIfcCartesianPoint([point[1], point[0]])
                                for point in profile
                            ]
                        ),
                    ),
                )
        # record profile(s) in an ExternalReference so we can find again
        self.createIfcExternalReferenceRelationship(
            identifier,
            None,
            self.createIfcExternalReference(None, identifier, None),
            closedprofiledefs,
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
            bodycontext,
            "Body",
            "AdvancedSweptSolid",
            [
                self.createIfcSurfaceCurveSweptAreaSolid(
                    closedprofiledef,
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


def createBrep_fromDXF(self, context, path_dxf):
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
    breps = []
    for entity in model:
        if entity.get_mode() == "AcDbPolyFaceMesh":
            ifc_faces = []
            for face in entity.faces():
                ifc_faces.append(
                    self.createIfcFace(
                        [
                            self.createIfcFaceOuterBound(
                                self.createIfcPolyLoop(
                                    [
                                        self.createIfcCartesianPoint(
                                            (face[index].dxf.location)
                                        )
                                        for index in range(len(face) - 1)
                                    ]
                                ),
                                True,
                            )
                        ]
                    )
                )
            breps.append(
                self.createIfcFacetedBrep(self.createIfcClosedShell(ifc_faces))
            )
    if len(breps) > 0:
        return self.createIfcShapeRepresentation(
            context,
            "Body",
            "Brep",
            breps,
        )


def createTessellation_fromDXF(self, context, path_dxf):
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
    tessellations = []
    for entity in model:
        if entity.get_mode() == "AcDbPolyFaceMesh":
            vertices, faces = entity.indexed_faces()
            pointlist = self.createIfcCartesianPointList3D(
                [vertex.dxf.location for vertex in vertices]
            )
            indexedfaces = [
                self.createIfcIndexedPolygonalFace(
                    [index + 1 for index in face.indices]
                )
                for face in faces
            ]
        tessellations.append(
            self.createIfcPolygonalFaceSet(pointlist, None, indexedfaces, None)
        )
    if len(tessellations) > 0:
        return self.createIfcShapeRepresentation(
            context,
            "Body",
            "Tessellation",
            tessellations,
        )


def assign_storey_byindex(self, entity, index):
    # let's see if there is an existing IfcBuildingStorey defined
    storeys = {}
    for storey in self.by_type("IfcBuildingStorey"):
        storeys[storey.Name] = storey
    run(
        "aggregate.assign_object",
        self,
        product=entity,
        relating_object=storeys[str(index)],
    )


def assign_representation_fromDXF(self, bodycontext, element, stylename, path_dxf):
    """Assign geometry from DXF unless a TypeProduct with this name already exists"""
    identifier = stylename + "/" + os.path.split(path_dxf)[-1]

    # let's see if there is an existing TypeProduct defined
    typeproducts = {}
    for typeproduct in self.by_type("IfcTypeProduct"):
        typeproducts[typeproduct.Name] = typeproduct

    if identifier in typeproducts:
        # The TypeProduct knows what MappedRepresentations to use
        for representationmap in typeproducts[identifier].RepresentationMaps:
            run(
                "geometry.assign_representation",
                self,
                product=element,
                representation=run(
                    "geometry.map_representation",
                    self,
                    representation=representationmap.MappedRepresentation,
                ),
            )
    else:
        # load a DXF polyface mesh as a Brep and create the TypeProduct
        brep = self.createBrep_fromDXF(
            bodycontext,
            path_dxf,
        )
        # create a mapped item that can be reused
        run(
            "geometry.assign_representation",
            self,
            product=run(
                "root.create_entity",
                self,
                ifc_class="IfcTypeProduct",
                name=identifier,
            ),
            representation=brep,
        )

        run(
            "geometry.assign_representation",
            self,
            product=element,
            representation=run(
                "geometry.map_representation", self, representation=brep
            ),
        )


setattr(ifcfile, "assign_representation_fromDXF", assign_representation_fromDXF)
setattr(ifcfile, "assign_storey_byindex", assign_storey_byindex)
setattr(ifcfile, "createCurve2D", createCurve2D)
setattr(ifcfile, "createSweptSolid", createSweptSolid)
setattr(ifcfile, "assign_extrusion_fromDXF", assign_extrusion_fromDXF)
setattr(ifcfile, "createAdvancedSweptSolid", createAdvancedSweptSolid)
setattr(ifcfile, "createBrep_fromDXF", createBrep_fromDXF)
setattr(ifcfile, "createTessellation_fromDXF", createTessellation_fromDXF)