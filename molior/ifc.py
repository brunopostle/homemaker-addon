from ifcopenshell.file import file as ifcfile
import ezdxf


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


def createBrep_fromDXF(self, context, path_dxf):
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
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
            return self.createIfcShapeRepresentation(
                context,
                "Body",
                "Brep",
                [self.createIfcFacetedBrep(self.createIfcClosedShell(ifc_faces))],
            )


def createTessellation_fromDXF(self, context, path_dxf):
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
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
            return self.createIfcShapeRepresentation(
                context,
                "Body",
                "Tessellation",
                [self.createIfcPolygonalFaceSet(pointlist, None, indexedfaces, None)],
            )


setattr(ifcfile, "createCurve2D", createCurve2D)
setattr(ifcfile, "createSweptSolid", createSweptSolid)
setattr(ifcfile, "createAdvancedSweptSolid", createAdvancedSweptSolid)
setattr(ifcfile, "createBrep_fromDXF", createBrep_fromDXF)
setattr(ifcfile, "createTessellation_fromDXF", createTessellation_fromDXF)
