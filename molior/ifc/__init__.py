""" Domain-specific extensions to IfcOpenShell

A collection of code for commonly used IFC related tasks, generally
implemented as methods overloaded onto ifcopenshell.file

"""

from ifcopenshell.file import file as ifcfile
import ezdxf
import os
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


def createExtrudedAreaSolid(self, profile, height, direction=[0.0, 0.0, 1.0]):
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


def clipSolid(self, solid, start, end):
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


def createTessellations_fromDXF(self, path_dxf):
    doc = ezdxf.readfile(path_dxf)
    model = doc.modelspace()
    tessellations = []
    for entity in model:
        if entity.get_mode() == "AcDbPolyFaceMesh":
            vertices, faces = entity.indexed_faces()

            tessellations.append(
                self.createTessellation_fromMesh(
                    [vertex.dxf.location for vertex in vertices],
                    [face.indices for face in faces],
                )
            )
    return tessellations


def createTessellation_fromMesh(self, vertices, faces):
    pointlist = self.createIfcCartesianPointList3D(vertices)
    indexedfaces = [
        self.createIfcIndexedPolygonalFace([index + 1 for index in face])
        for face in faces
    ]
    return self.createIfcPolygonalFaceSet(pointlist, None, indexedfaces, None)


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
        # load a DXF polyface mesh as a Tessellation and create the TypeProduct
        brep = self.createIfcShapeRepresentation(
            bodycontext,
            "Body",
            "Tessellation",
            self.createTessellations_fromDXF(path_dxf),
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
setattr(ifcfile, "createExtrudedAreaSolid", createExtrudedAreaSolid)
setattr(ifcfile, "clipSolid", clipSolid)
setattr(ifcfile, "createTessellation_fromMesh", createTessellation_fromMesh)
setattr(ifcfile, "assign_extrusion_fromDXF", assign_extrusion_fromDXF)
setattr(ifcfile, "createTessellations_fromDXF", createTessellations_fromDXF)
