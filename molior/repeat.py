import ifcopenshell.api

import molior
from molior.baseclass import TraceClass
from molior.geometry import add_2d, subtract_2d, scale_2d, distance_2d, matrix_align
from molior.ifc import (
    add_face_topology_epsets,
    assign_type_by_name,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
)
from molior.extrusion import Extrusion

run = ifcopenshell.api.run


class Repeat(TraceClass):
    """A row of evenly spaced identical objects"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.alternate = 0
        self.height = 0.0
        self.ceiling = 0.0
        self.ifc = "IfcBuildingElementProxy"
        self.predefined_type = "USERDEFINED"
        self.inset = 0.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.outer = 0.08
        self.material = "Sandstone"
        self.structural_material = "Concrete"
        self.structural_profile = [
            "IfcRectangleProfileDef",
            {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.2},
        ]
        self.path = []
        self.spacing = 1.0
        self.traces = []
        self.not_start = True
        self.not_end = True
        self.not_corner = False
        self.Extrusion = Extrusion
        self.Repeat = Repeat
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.identifier = self.style + "/" + self.name

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        style = molior.Molior.style
        myconfig = style.get(self.style)
        if self.asset in self.style_assets:
            for index in range(len(self.style_assets[self.asset])):
                height = self.style_assets[self.asset][index]["height"]
                if height >= self.height - self.ceiling:
                    break
            name = self.style_assets[self.asset][index]["file"]
        else:
            name = "error"

        segments = self.segments()
        self.outer += self.xshift

        for id_segment in range(segments):
            if self.length_segment(id_segment) < 2 * self.inset:
                continue
            inset = scale_2d(self.direction_segment(id_segment), self.inset)
            # outside face start and end coordinates
            v_out_a = add_2d(self.corner_out(id_segment), inset)
            v_out_b = subtract_2d(self.corner_out(id_segment + 1), inset)
            # space to fill
            length = distance_2d(v_out_a, v_out_b)
            if self.spacing > 0.0 and self.spacing < length:
                items = int(length / self.spacing) + 1
            else:
                items = 2

            spacing = length / (items - 1)

            if self.alternate == 1:
                items -= 1
                v_out_a = add_2d(
                    v_out_a, scale_2d(self.direction_segment(id_segment), spacing / 2)
                )

            aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.identifier,
                predefined_type=self.predefined_type,
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=aggregate,
                matrix=matrix_align(
                    [*self.corner_coor(id_segment), self.elevation],
                    [*self.corner_coor(id_segment + 1), self.elevation],
                ),
            )
            # assign the aggregate to a storey
            assign_storey_byindex(self.file, aggregate, self.building, self.level)

            if self.parent_aggregate != None:
                run(
                    "aggregate.assign_object",
                    self.file,
                    product=aggregate,
                    relating_object=self.parent_aggregate,
                )

            for index in range(items):
                location = add_2d(
                    v_out_a,
                    scale_2d(self.direction_segment(id_segment), index * spacing),
                )

                # fill space between
                if index != items - 1:
                    for condition in self.traces:
                        for name in myconfig["traces"]:
                            if name == condition:
                                config = myconfig["traces"][name]
                                vals = {
                                    "cellcomplex": self.cellcomplex,
                                    "closed": False,
                                    "path": [
                                        location,
                                        add_2d(
                                            location,
                                            scale_2d(
                                                self.direction_segment(id_segment),
                                                spacing,
                                            ),
                                        ),
                                    ],
                                    "file": self.file,
                                    "name": name,
                                    "elevation": self.elevation,
                                    "height": self.height - self.yshift,
                                    "ceiling": self.ceiling,
                                    "xshift": self.xshift,
                                    "yshift": self.yshift,
                                    "normals": self.normals,
                                    "normal_set": self.normal_set,
                                    "parent_aggregate": aggregate,
                                    "style": self.style,
                                    "building": self.building,
                                    "structural_analysis_model": self.structural_analysis_model,
                                    "level": self.level,
                                    "predefined_type": self.predefined_type,
                                    "style_assets": self.style_assets,
                                    "style_object": self.style_object,
                                }
                                vals.update(config)
                                part = getattr(self, config["class"])(vals)

                                part.execute()

                if (
                    index > 0
                    or (id_segment == 0 and not self.closed)
                    or self.inset > 0.0
                ):
                    if self.inset == 0.0:
                        if self.closed:
                            if index == items - 1 and self.not_corner:
                                continue
                        else:
                            if (
                                (index == 0 and id_segment == 0 and self.not_start)
                                or (
                                    index == items - 1
                                    and id_segment == segments - 1
                                    and self.not_end
                                )
                                or (
                                    index == items - 1
                                    and id_segment != segments - 1
                                    and self.not_corner
                                )
                            ):
                                continue

                    entity = run(
                        "root.create_entity",
                        self.file,
                        ifc_class=self.ifc,
                        name=self.identifier,
                        predefined_type=self.predefined_type,
                    )
                    self.add_psets(entity)
                    # place the entity in space
                    elevation = self.elevation + self.yshift
                    # assign the entity to the aggregate
                    run(
                        "aggregate.assign_object",
                        self.file,
                        product=entity,
                        relating_object=aggregate,
                    )

                    # structural stuff
                    if entity.is_a("IfcColumn") or entity.is_a("IfcMember"):
                        # TODO support IfcPile IfcFooting
                        # TODO skip unless Pset_MemberCommon.LoadBearing
                        start = [*location, self.elevation]
                        end = [*location, self.elevation + self.height]
                        structural_member = run(
                            "root.create_entity",
                            self.file,
                            ifc_class="IfcStructuralCurveMember",
                            name=self.name,
                        )
                        assignment = run(
                            "root.create_entity",
                            self.file,
                            ifc_class="IfcRelAssignsToProduct",
                        )
                        assignment.RelatingProduct = structural_member
                        assignment.RelatedObjects = [entity]
                        segment = self.chain.edges()[id_segment]
                        face = self.chain.graph[segment[0]][1]["face"]
                        back_cell = self.chain.graph[segment[0]][1]["back_cell"]
                        front_cell = self.chain.graph[segment[0]][1]["front_cell"]
                        add_face_topology_epsets(
                            self.file, structural_member, face, back_cell, front_cell
                        )
                        structural_member.PredefinedType = "RIGID_JOINED_MEMBER"
                        structural_member.Axis = self.file.createIfcDirection(
                            [*self.normal_segment(id_segment), 0.0]
                        )
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

                    if entity.is_a("IfcVirtualElement"):
                        continue
                    if not self.do_representation:
                        continue
                    run(
                        "geometry.edit_object_placement",
                        self.file,
                        product=entity,
                        matrix=matrix_align(
                            [*location, elevation],
                            [
                                *add_2d(location, self.direction_segment(id_segment)),
                                elevation,
                            ],
                        ),
                    )
                    assign_type_by_name(
                        self.file,
                        self.style_object,
                        element=entity,
                        stylename=self.style,
                        name=name,
                    )
                    # TODO Axis Representation
                    run(
                        "material.assign_material",
                        self.file,
                        product=entity,
                        material=get_material_by_name(
                            self.file,
                            self.style_object,
                            name=self.material,
                            stylename=self.style,
                        ),
                    )
