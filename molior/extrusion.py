import numpy
import ifcopenshell.api
from ifcopenshell.util.placement import a2p

from molior.baseclass import TraceClass
from molior.geometry import (
    normalise_3d,
    subtract_3d,
    magnitude_3d,
)
from molior.ifc import (
    add_face_topology_epsets,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
    get_type_object,
)

run = ifcopenshell.api.run


class Extrusion(TraceClass):
    """A profile following a horizontal 2D path"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcBuildingElementProxy"
        self.extension = 0.0
        self.scale = 1.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.structural_material = "Concrete"
        self.structural_profile = [
            "IfcRectangleProfileDef",
            {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.3},
        ]
        self.path = []
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""

        # contexts

        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        axis_context = get_context_by_name(self.file, context_identifier="Axis")
        body_context = get_context_by_name(self.file, context_identifier="Body")

        # type

        type_product = get_type_object(
            self.file,
            self.style_object,
            ifc_type=self.ifc + "Type",
            stylename=self.style,
            name=self.name,
        )

        # loop through segments

        first_element = None
        previous_element = None
        segments = self.segments()

        # aggregate all segments in the path

        if segments > 1:
            path_aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcElementAssembly",
                name=self.name,
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=path_aggregate,
            )

        for id_segment in range(segments):

            # create an element

            linear_element = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.name,
            )
            run(
                "type.assign_type",
                self.file,
                related_object=linear_element,
                relating_type=type_product,
            )
            if segments > 1:
                run(
                    "aggregate.assign_object",
                    self.file,
                    product=linear_element,
                    relating_object=path_aggregate,
                )

            # axis and matrix stuff

            start = [*self.corner_coor(id_segment), self.elevation + self.height]
            end = [*self.corner_coor(id_segment + 1), self.elevation + self.height]
            vector = subtract_3d(end, start)
            direction = normalise_3d(vector)
            length = magnitude_3d(vector)

            start_extension = 0.0
            end_extension = 0.0
            if self.closed or id_segment > 0:
                start_extension += 1.0
            if self.closed or id_segment < segments - 1:
                end_extension += 1.0
            if not self.closed and id_segment == 0:
                start_extension += self.extension
            if not self.closed and id_segment == segments - 1:
                end_extension += self.extension

            to_x_axis = [
                [0.0, 0.0, -1.0, length + end_extension],
                [-1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
            placement = a2p(start, [0.0, 0.0, 1.0], direction)
            matrix = placement @ to_x_axis
            inverse = numpy.linalg.inv(matrix)

            # clip ends

            clippings = []

            clipping_matrix_start = self.clipping_plane(id_segment)
            clipping_matrix_end = self.clipping_plane(id_segment + 1)
            clipping_matrix_end[0][2] = -clipping_matrix_end[0][2]
            clipping_matrix_end[1][2] = -clipping_matrix_end[1][2]

            if self.closed or id_segment > 0:
                clippings.append(
                    {
                        "type": "IfcBooleanClippingResult",
                        "operand_type": "IfcHalfSpaceSolid",
                        "matrix": (inverse @ clipping_matrix_start).tolist(),
                    }
                )
            if self.closed or id_segment < segments - 1:
                clippings.append(
                    {
                        "type": "IfcBooleanClippingResult",
                        "operand_type": "IfcHalfSpaceSolid",
                        "matrix": (inverse @ clipping_matrix_end).tolist(),
                    }
                )

            # connect ends

            if previous_element:
                run(
                    "geometry.connect_path",
                    self.file,
                    relating_element=linear_element,
                    related_element=previous_element,
                    relating_connection="ATEND",
                    related_connection="ATSTART",
                    description="MITRE",
                )
            else:
                first_element = linear_element

            previous_element = linear_element

            if self.closed and id_segment == segments - 1:
                run(
                    "geometry.connect_path",
                    self.file,
                    relating_element=first_element,
                    related_element=linear_element,
                    relating_connection="ATEND",
                    related_connection="ATSTART",
                    description="MITRE",
                )

            # representations

            material_profiles = []
            profile_set = None
            for association in type_product.HasAssociations:
                if association.is_a(
                    "IfcRelAssociatesMaterial"
                ) and association.RelatingMaterial.is_a("IfcMaterialProfileSet"):
                    profile_set = association.RelatingMaterial
                    material_profiles = association.RelatingMaterial.MaterialProfiles

            shape_representation = run(
                "geometry.add_profile_representation",
                self.file,
                context=body_context,
                profile=material_profiles[0].Profile,
                depth=length + start_extension + end_extension,
                clippings=clippings,
            )

            run(
                "geometry.assign_representation",
                self.file,
                product=linear_element,
                representation=shape_representation,
            )

            axis_representation = run(
                "geometry.add_axis_representation",
                self.file,
                context=axis_context,
                axis=[[0.0, 0.0, 0.0], [0.0, 0.0, length]],
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=linear_element,
                representation=axis_representation,
            )

            # location

            shift_matrix = [
                [1.0, 0.0, 0.0, self.xshift],
                [0.0, 1.0, 0.0, self.yshift],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]

            run(
                "geometry.edit_object_placement",
                self.file,
                product=linear_element,
                matrix=matrix @ shift_matrix,
            )

            # structural stuff

            if (
                linear_element.is_a("IfcBeam")
                or linear_element.is_a("IfcFooting")
                or linear_element.is_a("IfcMember")
            ):
                # TODO skip unless Pset_MemberCommon.LoadBearing
                # generate structural edges
                structural_member = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcStructuralCurveMember",
                    name=self.style + "/" + self.name,
                    predefined_type="RIGID_JOINED_MEMBER",
                )
                assignment = run(
                    "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
                )
                assignment.RelatingProduct = structural_member
                assignment.RelatedObjects = [linear_element]

                segment = self.chain.edges()[id_segment]
                face = self.chain.graph[segment[0]][1]["face"]
                back_cell = self.chain.graph[segment[0]][1]["back_cell"]
                front_cell = self.chain.graph[segment[0]][1]["front_cell"]
                add_face_topology_epsets(
                    self.file, structural_member, face, back_cell, front_cell
                )
                structural_member.Axis = self.file.createIfcDirection([0.0, 0.0, 1.0])
                run(
                    "structural.assign_structural_analysis_model",
                    self.file,
                    product=structural_member,
                    structural_analysis_model=self.structural_analysis_model,
                )
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=structural_member,
                    representation=self.file.createIfcTopologyRepresentation(
                        reference_context,
                        reference_context.ContextIdentifier,
                        "Edge",
                        [
                            self.file.createIfcEdge(
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(start)
                                ),
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(end)
                                ),
                            )
                        ],
                    ),
                )
                # FIXME get Type as per Grillage
                profile = self.file.create_entity(
                    self.structural_profile[0], **self.structural_profile[1]
                )
                rel = run(
                    "material.assign_material",
                    self.file,
                    product=structural_member,
                    type="IfcMaterialProfileSet",
                )
                profile_set = rel.RelatingMaterial
                material_profile = run(
                    "material.add_profile",
                    self.file,
                    profile_set=profile_set,
                    material=get_material_by_name(
                        self.file,
                        self.style_object,
                        name=self.structural_material,
                        stylename=self.style,
                    ),
                )
                run(
                    "material.assign_profile",
                    self.file,
                    material_profile=material_profile,
                    profile=profile,
                )

        # segments done

        if segments > 1:
            top_object = path_aggregate
        else:
            top_object = linear_element
        if self.parent_aggregate != None:
            run(
                "aggregate.assign_object",
                self.file,
                product=top_object,
                relating_object=self.parent_aggregate,
            )
        else:
            assign_storey_byindex(self.file, top_object, self.building, self.level)

        return top_object
