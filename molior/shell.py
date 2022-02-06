import ifcopenshell.api

from topologist.helpers import string_to_coor, el
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d
from molior.ifc import (
    add_face_topology_epsets,
    create_extruded_area_solid,
    create_curve_bounded_plane,
    create_face_surface,
    assign_storey_byindex,
    get_material_by_name,
)

run = ifcopenshell.api.run


class Shell(BaseClass):
    """A pitched roof or soffit"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcRoof"
        self.predefined_type = "USERDEFINED"
        self.layerset = [[0.03, "Plaster"], [0.2, "Insulation"], [0.05, "Tiles"]]
        self.structural_material = "Concrete"
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

        inclines = []
        uniform_pitch = False
        for face in self.hull.faces:
            normal = face[1]["face"].Normal()
            inclines.append(normal[2])
        if abs(max(inclines) - min(inclines)) < 0.01:
            uniform_pitch = True

        elevation = None
        for face in self.hull.faces:
            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]
            normal = face[1]["face"].Normal()
            # need this for boundaries
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
            # need this for structure
            face_surface = create_face_surface(self.file, vertices, normal)
            for vertex in vertices:
                if elevation == None or vertex[2] < elevation:
                    elevation = el(vertex[2])

            element = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.identifier,
            )
            run(
                "aggregate.assign_object",
                self.file,
                product=element,
                relating_object=aggregate,
            )
            add_face_topology_epsets(
                self.file,
                element,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )

            # generate space boundar(y|ies)
            for mycell in face[1]["back_cell"], face[1]["front_cell"]:
                if mycell:
                    boundary = run(
                        "root.create_entity",
                        self.file,
                        ifc_class="IfcRelSpaceBoundary2ndLevel",
                    )
                    boundary.ConnectionGeometry = (
                        self.file.createIfcConnectionSurfaceGeometry(
                            create_curve_bounded_plane(self.file, nodes_2d, matrix)
                        )
                    )
                    if element.is_a("IfcVirtualElement"):
                        boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                    else:
                        boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    boundary.InternalOrExternalBoundary = "EXTERNAL"
                    boundary.RelatedBuildingElement = element

                    cell_index = mycell.Get("index")
                    if cell_index != None:
                        # can't assign psets to an IfcRelationship, use Description instead
                        boundary.Description = "CellIndex " + str(cell_index)
                    face_index = face[1]["face"].Get("index")
                    if face_index != None:
                        boundary.Name = "FaceIndex " + face_index

            if element.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # generate structural surfaces
            structural_surface = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.identifier,
                predefined_type="SHELL",
            )
            add_face_topology_epsets(
                self.file,
                structural_surface,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            structural_surface.Thickness = self.thickness
            run(
                "structural.assign_structural_analysis_model",
                self.file,
                product=structural_surface,
                structural_analysis_model=self.structural_analysis_model,
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
                material=get_material_by_name(
                    self.file,
                    reference_context,
                    self.structural_material,
                    self.style_materials,
                ),
            )

            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [element]

            # get or create a Type
            myelement_type = self.get_element_type()
            run(
                "type.assign_type",
                self.file,
                related_object=element,
                relating_type=myelement_type,
            )
            self.add_psets(myelement_type)

            # Usage isn't created until after type.assign_type
            for inverse in self.file.get_inverse(
                ifcopenshell.util.element.get_material(myelement_type)
            ):
                if inverse.is_a("IfcMaterialLayerSetUsage"):
                    inverse.OffsetFromReferenceLine = 0.0 - self.inner

            # create a representation
            if float(normal_x[2]) < 0.001 or not uniform_pitch:
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
                    create_extruded_area_solid(
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
                product=element,
                representation=shape,
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=element,
                matrix=matrix,
            )
        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        assign_storey_byindex(self.file, aggregate, self.building, level)
