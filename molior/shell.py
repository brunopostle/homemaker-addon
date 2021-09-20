import ifcopenshell.api

from topologist.helpers import string_to_coor
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d
from molior.ifc import (
    createExtrudedAreaSolid,
    createCurveBoundedPlane,
    createFaceSurface,
    assign_storey_byindex,
    get_material_by_name,
)

run = ifcopenshell.api.run


class Shell(BaseClass):
    """A pitched roof or soffit"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ifc = "IfcRoof"
        self.predefined_type = "USERDEFINED"
        self.layerset = [[0.03, "Plaster"], [0.2, "Insulation"], [0.05, "Tiles"]]
        self.inner = 0.08
        self.outer = 0.20
        self.type = "molior-shell"
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]
        self.identifier = self.style + "/" + self.name

    def execute(self):
        """Generate some ifc"""
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Reference":
                reference_context = item
            if item.ContextIdentifier == "Body":
                body_context = item
        aggregate = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.identifier,
        )
        # FIXME this puts roofs in the ground floor
        assign_storey_byindex(self.file, aggregate, 0)
        for face in self.hull.faces:
            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]
            normal = face[1]
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
            # need this for structure
            face_surface = createFaceSurface(self.file, vertices, normal)

            # generate structural surfaces
            structural_surface = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.identifier,
            )
            self.add_topology_pset(structural_surface, *face[2])
            structural_surface.PredefinedType = "SHELL"
            structural_surface.Thickness = self.thickness
            run(
                "structural.assign_structural_analysis_model",
                self.file,
                product=structural_surface,
                structural_analysis_model=self.file.by_type(
                    "IfcStructuralAnalysisModel"
                )[0],
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=structural_surface,
                representation=self.file.createIfcTopologyRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Face",
                    [face_surface],
                ),
            )
            run(
                "material.assign_material",
                self.file,
                product=structural_surface,
                material=get_material_by_name(self.file, reference_context, "Concrete"),
            )

            entity = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.identifier,
            )
            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [entity]
            run(
                "aggregate.assign_object",
                self.file,
                product=entity,
                relating_object=aggregate,
            )
            self.add_topology_pset(entity, *face[2])

            myelement_type = self.get_element_type()
            run(
                "type.assign_type",
                self.file,
                related_object=entity,
                relating_type=myelement_type,
            )
            self.add_psets(myelement_type)

            # Usage isn't created until after type.assign_type
            mylayerset = ifcopenshell.util.element.get_material(myelement_type)
            for inverse in self.file.get_inverse(mylayerset):
                if inverse.is_a("IfcMaterialLayerSetUsage"):
                    inverse.OffsetFromReferenceLine = 0.0 - self.inner

            if abs(float(normal_x[2])) < 0.001:
                extrude_height = self.outer
                extrude_direction = [0.0, 0.0, 1.0]
            else:
                extrude_height = self.outer / float(normal_x[2])
                extrude_direction = [
                    0.0,
                    0 - float(normal_x[1]),
                    float(normal_x[2]),
                ]
            shape = self.file.createIfcShapeRepresentation(
                body_context,
                "Body",
                "SweptSolid",
                [
                    createExtrudedAreaSolid(
                        self.file,
                        nodes_2d,
                        extrude_height,
                        extrude_direction,
                    )
                ],
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=entity,
                representation=shape,
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=entity,
                matrix=matrix,
            )

            # generate space boundary for back cell
            if face[2][1]:
                boundary = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcRelSpaceBoundary2ndLevel",
                )
                boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                boundary.InternalOrExternalBoundary = "EXTERNAL"
                boundary.RelatedBuildingElement = entity
                boundary.ConnectionGeometry = (
                    self.file.createIfcConnectionSurfaceGeometry(
                        createCurveBoundedPlane(self.file, nodes_2d, matrix)
                    )
                )

                cell_index = face[2][1].Get("index")
                if not cell_index == None:
                    # can't assign psets to an IfcRelationship, use Description instead
                    boundary.Description = "CellIndex " + str(cell_index)
