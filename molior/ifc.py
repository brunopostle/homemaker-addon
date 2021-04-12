from ifcopenshell.file import file as ifcfile
import ezdxf
import os
import ifcopenshell.api

run = ifcopenshell.api.run


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

    # let's see if there is an existing ExternalReference defined
    externalreferences = {}
    for externalreference in self.by_type("IfcExternalReferenceRelationship"):
        externalreferences[externalreference.Name] = externalreference

    if identifier in externalreferences:
        # We already have this profile definition
        closedprofiledefs = externalreferences[identifier].RelatedResourceObjects

    else:
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
        self.createIfcExternalReferenceRelationship(
            identifier,
            None,
            self.createIfcExternalReference(None, identifier, None),
            closedprofiledefs,
        )

    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )
    polyline = self.createIfcPolyline(
        [self.createIfcCartesianPoint(point) for point in directrix]
    )
    plane = self.createIfcPlane(axis)
    shape2 = self.createIfcShapeRepresentation(
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
    )

    run("geometry.assign_representation", self, product=element, representation=shape2)


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
setattr(ifcfile, "createCurve2D", createCurve2D)
setattr(ifcfile, "createSweptSolid", createSweptSolid)
setattr(ifcfile, "assign_extrusion_fromDXF", assign_extrusion_fromDXF)
setattr(ifcfile, "createAdvancedSweptSolid", createAdvancedSweptSolid)
setattr(ifcfile, "createBrep_fromDXF", createBrep_fromDXF)
setattr(ifcfile, "createTessellation_fromDXF", createTessellation_fromDXF)
