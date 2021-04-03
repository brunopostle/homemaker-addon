from ifcopenshell.file import file as ifcfile


def createSweptSolid(self, context, footprint, height):
    """A simple vertically extruded profile"""
    if not footprint[-1] == footprint[0]:
        # a closed polyline has first and last points coincident
        footprint.append(footprint[0])

    profile = self.createIfcArbitraryClosedProfileDef(
        "AREA",
        None,
        self.createIfcPolyline(
            [self.createIfcCartesianPoint(point) for point in footprint]
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


setattr(ifcfile, "createSweptSolid", createSweptSolid)
