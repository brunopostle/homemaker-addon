import ifcopenshell.api

import molior
from molior.baseclass import TraceClass
from molior.geometry import matrix_align, add_2d, distance_2d
from molior.ifc import (
    add_face_topology_epsets,
    assign_storey_byindex,
    assign_extrusion_fromDXF,
    get_material_by_name,
    get_context_by_name,
)

run = ifcopenshell.api.run


class Extrusion(TraceClass):
    """A profile following a horizontal 2D path"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcBuildingElementProxy"
        self.predefined_type = "USERDEFINED"
        self.closed = 0
        self.extension = 0.0
        self.scale = 1.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.material = "Travertine"
        self.structural_material = "Concrete"
        self.structural_profile = [
            "IfcRectangleProfileDef",
            {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.3},
        ]
        self.path = []
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.identifier = self.style + "/" + self.name

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        style = molior.Molior.style
        element = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.identifier,
            predefined_type=self.predefined_type,
        )
        self.add_psets(element)

        if (
            element.is_a("IfcBeam")
            or element.is_a("IfcFooting")
            or element.is_a("IfcMember")
        ):
            # TODO skip unless Pset_MemberCommon.LoadBearing
            # generate structural edges
            segments = self.segments()
            for id_segment in range(segments):
                start = [*self.corner_coor(id_segment), self.elevation + self.height]
                end = [*self.corner_coor(id_segment + 1), self.elevation + self.height]
                structural_member = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcStructuralCurveMember",
                    name=self.identifier,
                    predefined_type="RIGID_JOINED_MEMBER",
                )
                assignment = run(
                    "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
                )
                assignment.RelatingProduct = structural_member
                assignment.RelatedObjects = [element]

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
                # FIXME create Type and Profile Set using get_extruded_type_by_name()
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
                        context_identifier="Reference",
                        name=self.structural_material,
                        style_materials=self.style_materials,
                    ),
                )
                run(
                    "material.assign_profile",
                    self.file,
                    material_profile=material_profile,
                    profile=profile,
                )

        run(
            "material.assign_material",
            self.file,
            product=element,
            material=get_material_by_name(
                self.file,
                context_identifier="Body",
                name=self.material,
                style_materials=self.style_materials,
            ),
        )

        assign_storey_byindex(self.file, element, self.building, self.level)
        directrix = self.path
        if self.closed:
            directrix.append(directrix[0])
        else:
            # FIXME merge continuing extrusions when profile/material is the same
            directrix[0] = add_2d(directrix[0], self.extension_start())
            directrix[-1] = add_2d(directrix[-1], self.extension_end())

        if self.parent_aggregate != None:
            run(
                "aggregate.assign_object",
                self.file,
                product=element,
                relating_object=self.parent_aggregate,
            )

        if self.segments() == 1 and distance_2d(directrix[0], directrix[1]) < 0.001:
            # better not to create a representation for zero length extrusions
            return
        if not self.do_representation:
            return

        dxf_path = style.get_file(self.style, self.profile)

        transform = self.file.createIfcCartesianTransformationOperator2D(
            None,
            None,
            self.file.createIfcCartesianPoint([self.yshift, self.xshift]),
            self.scale,
        )

        # TODO Axis Representation
        assign_extrusion_fromDXF(
            self.file,
            context_identifier="Body",
            element=element,
            directrix=directrix,
            stylename=self.style,
            path_dxf=dxf_path,
            transform=transform,
        )

        run(
            "geometry.edit_object_placement",
            self.file,
            product=element,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.height], [1.0, 0.0, 0.0]
            ),
        )
