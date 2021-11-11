import ifcopenshell.api

import molior
from molior.baseclass import TraceClass
from molior.geometry import add_2d, subtract_2d, scale_2d, distance_2d, matrix_align
from molior.ifc import (
    assign_representation_fromDXF,
    assign_storey_byindex,
    get_material_by_name,
)
from molior.extrusion import Extrusion

run = ifcopenshell.api.run


class Repeat(TraceClass):
    """A row of evenly spaced identical objects"""

    def __init__(self, args={}):
        super().__init__(args)
        self.alternate = 0
        self.closed = 0
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
        self.path = []
        self.spacing = 1.0
        self.traces = []
        self.type = "molior-repeat"
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
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Reference":
                reference_context = item
            if item.ContextIdentifier == "Body":
                body_context = item
        style = molior.Molior.style
        myconfig = style.get(self.style)
        if self.asset in self.style_assets:
            for index in range(len(self.style_assets[self.asset])):
                height = self.style_assets[self.asset][index]["height"]
                if height >= self.height - self.ceiling:
                    break
            dxf_path = style.get_file(
                self.style, self.style_assets[self.asset][index]["file"]
            )
        else:
            dxf_path = style.get_file(self.style, "error.dxf")

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
            # assign the aggregate to a storey
            assign_storey_byindex(self.file, aggregate, self.level)

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
                                    "closed": 0,
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
                                    "style": self.style,
                                    "level": self.level,
                                    "predefined_type": self.predefined_type,
                                    "style_assets": self.style_assets,
                                    "style_materials": self.style_materials,
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
                    # assign the entity to the aggregate
                    run(
                        "aggregate.assign_object",
                        self.file,
                        product=entity,
                        relating_object=aggregate,
                    )
                    # load geometry from a DXF file and assign to the entity
                    assign_representation_fromDXF(
                        self.file, body_context, entity, self.style, dxf_path
                    )
                    run(
                        "material.assign_material",
                        self.file,
                        product=entity,
                        material=get_material_by_name(
                            self.file, body_context, self.material, self.style_materials
                        ),
                    )

                    # structural stuff
                    if entity.is_a("IfcColumn"):
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
                        face = self.chain.graph[segment[0]][1][2]
                        back_cell = self.chain.graph[segment[0]][1][3]
                        front_cell = self.chain.graph[segment[0]][1][4]
                        self.add_topology_pset(
                            structural_member, face, back_cell, front_cell
                        )
                        structural_member.PredefinedType = "RIGID_JOINED_MEMBER"
                        structural_member.Axis = self.file.createIfcDirection(
                            [*self.normal_segment(id_segment), 0.0]
                        )
                        run(
                            "structural.assign_structural_analysis_model",
                            self.file,
                            product=structural_member,
                            structural_analysis_model=self.file.by_type(
                                "IfcStructuralAnalysisModel"
                            )[0],
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
                        # TODO define profile in style
                        profile = self.file.create_entity(
                            "IfcRectangleProfileDef",
                            ProfileType="AREA",
                            XDim=0.2,
                            YDim=0.2,
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
                                reference_context,
                                self.structural_material,
                                self.style_materials,
                            ),
                        )
                        run(
                            "material.assign_profile",
                            self.file,
                            material_profile=material_profile,
                            profile=profile,
                        )
