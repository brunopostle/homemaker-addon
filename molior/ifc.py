from ifcopenshell.file import file as ifcfile


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


setattr(ifcfile, "createSweptSolid", createSweptSolid)
setattr(ifcfile, "createAdvancedSweptSolid", createAdvancedSweptSolid)
