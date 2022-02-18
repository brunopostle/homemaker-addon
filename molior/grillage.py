import ifcopenshell.api

from topologist.helpers import string_to_coor, el
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d, matrix_align
from molior.ifc import (
    add_face_topology_epsets,
    create_extruded_area_solid,
    create_curve_bounded_plane,
    create_face_surface,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
    get_extruded_type_by_name,
)

run = ifcopenshell.api.run


class Grillage(BaseClass):
    """planar feature consisting of repeated linear elements"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcBuildingElementProxy"
        self.predefined_type = "USERDEFINED"
        self.structural_material = "Concrete"
        self.profiles = [
            {
                "ifc_class": "IfcRectangleProfileDef",
                "material": "Concrete",
                "parameters": {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.2},
                "position": {"Location": [0.0, 0.0], "RefDirection": [1.0, 0.0]},
            }
        ]
        self.outer = 0.20
        self.thickness = 0.4
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.inner = self.thickness - self.outer
        self.identifier = self.style + "/" + self.name

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        body_context = get_context_by_name(self.file, context_identifier="Body")

        aggregate = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.identifier,
        )

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

            face_aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.identifier,
            )
            run(
                "aggregate.assign_object",
                self.file,
                product=face_aggregate,
                relating_object=aggregate,
            )
            add_face_topology_epsets(
                self.file,
                face_aggregate,
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
                    if face_aggregate.is_a("IfcVirtualElement"):
                        boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                    else:
                        boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    boundary.InternalOrExternalBoundary = "EXTERNAL"
                    boundary.RelatedBuildingElement = face_aggregate

                    cell_index = mycell.Get("index")
                    if cell_index != None:
                        # can't assign psets to an IfcRelationship, use Description instead
                        boundary.Description = "CellIndex " + str(cell_index)
                    face_index = face[1]["face"].Get("index")
                    if face_index != None:
                        boundary.Name = "FaceIndex " + face_index

            if face_aggregate.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # FIXME should generate Structural Curve Member for each extrusion
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
            assignment.RelatedObjects = [face_aggregate]

            # generate repeating grillage elements

            run(
                "geometry.edit_object_placement",
                self.file,
                product=face_aggregate,
                matrix=matrix,
            )

            # create a box representing the outer extents for clipping the repeating elements
            extrude_direction = [0.0, 0.0, 1.0]
            matrix_clippy = matrix @ matrix_align(
                [0.0, 0.0, -self.inner], [1.0, 0.0, 0.0]
            )
            clippy = create_extruded_area_solid(
                self.file,
                nodes_2d,
                self.thickness,
                extrude_direction,
            )

            # create a Type for the extrusion
            product_type = get_extruded_type_by_name(
                self.file,
                style_materials=self.style_materials,
                profiles=self.profiles,
                context_identifier="Body",
                ifc_type=self.ifc + "Type",
                name=self.identifier,
                stylename=self.style,
            )
            product_type.PredefinedType = self.predefined_type
            self.add_psets(product_type)

            # FIXME set range, spacing, start, and length of linear elements
            for index in range(-5, 5):

                # create an element to host all extrusions
                linear_element = run(
                    "root.create_entity",
                    self.file,
                    ifc_class=self.ifc,
                    name=self.identifier,
                )
                csg_list = []
                for material_profile in product_type.HasAssociations[
                    0
                ].RelatingMaterial.MaterialProfiles:

                    # extrude each profile in the profile set
                    extrusion = self.file.createIfcExtrudedAreaSolid(
                        material_profile.Profile,
                        self.file.createIfcAxis2Placement3D(
                            self.file.createIfcCartesianPoint(
                                [float(index), -5.0, 0.0]
                            ),
                            self.file.createIfcDirection([0.0, 1.0, 0.0]),
                            self.file.createIfcDirection([1.0, 0.0, 0.0]),
                        ),
                        self.file.createIfcDirection([0.0, 0.0, 1.0]),
                        10.0,
                    )

                    # clip it
                    csg_list.append(
                        self.file.createIfcBooleanResult(
                            "INTERSECTION", extrusion, clippy
                        )
                    )

                shape_representation = self.file.createIfcShapeRepresentation(
                    body_context,
                    body_context.ContextIdentifier,
                    "CSG",
                    csg_list,
                )
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=linear_element,
                    representation=shape_representation,
                )
                run(
                    "material.assign_material",
                    self.file,
                    product=linear_element,
                    material=product_type.HasAssociations[0].RelatingMaterial,
                )

                # Somehow this performs a boolean intersection
                # run(
                #     "type.assign_type",
                #     self.file,
                #     related_object=linear_element,
                #     relating_type=product_type,
                # )

                # apparently aggregated elements need to be placed independently of the aggregate
                run(
                    "geometry.edit_object_placement",
                    self.file,
                    product=linear_element,
                    matrix=matrix_clippy,
                )

                # stuff the element into the face aggregate
                run(
                    "aggregate.assign_object",
                    self.file,
                    product=linear_element,
                    relating_object=face_aggregate,
                )

        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        assign_storey_byindex(self.file, aggregate, self.building, level)
