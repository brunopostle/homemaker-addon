from ifcopenshell.file import file as ifcfile
import ezdxf


def createSweptSolid(self, context, profile, height):
    """A simple vertically extruded profile"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last points coincident
        profile.append(profile[0])

    profile = self.createIfcArbitraryClosedProfileDef(
        "AREA",
        None,
        self.createIfcPolyline(
            [self.createIfcCartesianPoint(point) for point in profile]
        ),
    )
    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )
    direction = self.createIfcDirection([0.0, 0.0, 1.0])

    return self.createIfcShapeRepresentation(
        context,
        "Body",
        "SweptSolid",
        [self.createIfcExtrudedAreaSolid(profile, axis, direction, height)],
    )


def createAdvancedSweptSolid(self, context, profile, directrix):
    """A simple horizontally extruded profile following a directrix path"""
    if not profile[-1] == profile[0]:
        # a closed polyline has first and last points coincident
        profile.append(profile[0])

    profile = self.createIfcArbitraryClosedProfileDef(
        "AREA",
        None,
        self.createIfcPolyline(
            [self.createIfcCartesianPoint(point) for point in profile]
        ),
    )
    axis = self.createIfcAxis2Placement3D(
        self.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None
    )
    surface = self.createIfcPlane(axis)
    directrix = self.createIfcPolyline(
        [self.createIfcCartesianPoint(point) for point in directrix]
    )

    return self.createIfcShapeRepresentation(
        context,
        "Body",
        "AdvancedSweptSolid",
        [
            self.createIfcSurfaceCurveSweptAreaSolid(
                profile, axis, directrix, 0.0, 1.0, surface
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


setattr(ifcfile, "createSweptSolid", createSweptSolid)
setattr(ifcfile, "createAdvancedSweptSolid", createAdvancedSweptSolid)
setattr(ifcfile, "createBrep_fromDXF", createBrep_fromDXF)
