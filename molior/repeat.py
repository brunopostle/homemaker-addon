import numpy as np
import ifcopenshell.api.attribute
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.structural

from .baseclass import TraceClass
from .geometry import add_2d, subtract_2d, scale_2d, distance_2d, matrix_align
from .ifc import (
    add_face_topology_epsets,
    assign_structural_profile,
    is_load_bearing,
    assign_storey_byindex,
    get_type_object,
    get_context_by_name,
)
from .extrusion import Extrusion

api = ifcopenshell.api


class Repeat(TraceClass):
    """A row of evenly spaced identical objects"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.alternate = 0
        self.height = 0.0
        self.ceiling = 0.0
        self.ifc = "IfcBuildingElementProxy"
        self.inset = 0.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.offset = -0.08
        # None to take them from the Type, see assign_structural_profile()
        self.structural_material = None
        self.structural_profile = None
        self.path = []
        self.spacing = 1.0
        self.ref_direction = None
        self.traces = []
        self.not_start = True
        self.not_end = True
        self.not_corner = False
        self.Extrusion = Extrusion
        self.Repeat = Repeat
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference", target_view="GRAPH_VIEW"
        )
        axis_context = get_context_by_name(self.file, context_identifier="Axis")
        from . import Molior

        style = Molior.style
        myconfig = style.get(self.style)
        # the Type is drawn from 0.0 to the height of its family member
        type_height = self.height - self.ceiling
        if self.family in self.style_families:
            for index in range(len(self.style_families[self.family])):
                type_height = self.style_families[self.family][index]["height"]
                if type_height >= self.height - self.ceiling:
                    break
            asset_name = self.style_families[self.family][index]["typename"]
        else:
            asset_name = "error"

        segments = self.segments()
        self.offset -= self.xshift

        # aggregate all segments in the path

        if segments > 1:
            path_aggregate = api.root.create_entity(
                self.file,
                ifc_class="IfcElementAssembly",
                name=self.name,
            )
            api.geometry.edit_object_placement(
                self.file,
                product=path_aggregate,
            )

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

            aggregate = api.root.create_entity(
                self.file,
                ifc_class="IfcElementAssembly",
                name=self.name,
            )
            if segments > 1:
                api.aggregate.assign_object(
                    self.file,
                    products=[aggregate],
                    relating_object=path_aggregate,
                )
            api.geometry.edit_object_placement(
                self.file,
                product=aggregate,
                matrix=matrix_align(
                    [*self.corner_coor(id_segment), self.elevation],
                    [*self.corner_coor(id_segment + 1), self.elevation],
                ),
            )

            if self.parent_aggregate is not None:
                api.aggregate.assign_object(
                    self.file,
                    products=[aggregate],
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
                                    "ref_direction": self.ref_direction,
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
                                    "style_families": self.style_families,
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

                    entity = api.root.create_entity(
                        self.file,
                        ifc_class=self.ifc,
                        name=self.name,
                    )
                    # assign the entity to the aggregate
                    api.aggregate.assign_object(
                        self.file,
                        products=[entity],
                        relating_object=aggregate,
                    )

                    # structural stuff

                    is_foundation = entity.is_a("IfcPile") or entity.is_a("IfcFooting")
                    if (
                        (
                            entity.is_a("IfcColumn")
                            or entity.is_a("IfcMember")
                            or is_foundation
                        )
                        and hasattr(self, "chain")
                        and (not is_foundation or type_height > 0.0)
                        and is_load_bearing(
                            get_type_object(
                                self.file,
                                self.style_object,
                                ifc_type=self.ifc + "Type",
                                stylename=self.style,
                                name=asset_name,
                            )
                        )
                    ):
                        start = [*location, self.elevation]
                        end = [*location, self.elevation + self.height]
                        if is_foundation:
                            # a pile or pad hangs below the trace, as a footing
                            # trace has no height, the member is the Element
                            # itself, connect_structure() supports its base
                            start = [*location, self.elevation + self.yshift]
                            end = [
                                *location,
                                self.elevation + self.yshift + type_height,
                            ]
                        structural_member = api.root.create_entity(
                            self.file,
                            ifc_class="IfcStructuralCurveMember",
                            name=self.style + "/" + self.name,
                        )
                        api.structural.assign_product(
                            self.file,
                            relating_product=structural_member,
                            related_object=entity,
                        )
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
                        api.structural.assign_structural_analysis_model(
                            self.file,
                            products=[structural_member],
                            structural_analysis_model=self.structural_analysis_model,
                        )
                        api.geometry.assign_representation(
                            self.file,
                            product=structural_member,
                            representation=api.geometry.add_topology_representation(
                                self.file,
                                context=reference_context,
                                item=self.file.createIfcEdge(
                                    self.file.createIfcVertexPoint(
                                        self.file.createIfcCartesianPoint(start)
                                    ),
                                    self.file.createIfcVertexPoint(
                                        self.file.createIfcCartesianPoint(end)
                                    ),
                                ),
                            ),
                        )
                        assign_structural_profile(
                            self.file,
                            structural_member,
                            get_type_object(
                                self.file,
                                self.style_object,
                                ifc_type=self.ifc + "Type",
                                stylename=self.style,
                                name=asset_name,
                            ),
                            self.style_object,
                            stylename=self.style,
                            profile=self.structural_profile,
                            material=self.structural_material,
                        )

                    # representation

                    if entity.is_a("IfcVirtualElement"):
                        continue
                    if not self.do_representation:
                        continue

                    type_product = get_type_object(
                        self.file,
                        self.style_object,
                        ifc_type=self.ifc + "Type",
                        stylename=self.style,
                        name=asset_name,
                    )
                    # the Axis goes in the Type, occurrences get a mapped copy
                    type_identifiers = [
                        representation_map.MappedRepresentation.RepresentationIdentifier
                        for representation_map in type_product.RepresentationMaps or []
                    ]
                    if (
                        entity.is_a("IfcColumn") or entity.is_a("IfcMember")
                    ) and "Axis" not in type_identifiers:
                        api.geometry.assign_representation(
                            self.file,
                            product=type_product,
                            representation=api.geometry.add_axis_representation(
                                self.file,
                                context=axis_context,
                                axis=[[0.0, 0.0, 0.0], [0.0, 0.0, type_height]],
                            ),
                        )
                    api.type.assign_type(
                        self.file,
                        related_objects=[entity],
                        relating_type=type_product,
                    )

                    # place the entity in space
                    elevation = self.elevation + self.yshift
                    placement_matrix = matrix_align(
                        [*location, elevation],
                        [
                            *add_2d(location, self.direction_segment(id_segment)),
                            elevation,
                        ],
                    )

                    if self.ref_direction:
                        vertical_matrix = np.array(
                            [
                                [1.0, 0.0, 0.0, 0.0],
                                [
                                    0.0,
                                    self.ref_direction[0],
                                    self.ref_direction[1],
                                    0.0,
                                ],
                                [
                                    0.0,
                                    -self.ref_direction[1],
                                    self.ref_direction[0],
                                    0.0,
                                ],
                                [0.0, 0.0, 0.0, 1.0],
                            ]
                        )
                        placement_matrix = placement_matrix @ vertical_matrix

                    api.geometry.edit_object_placement(
                        self.file,
                        product=entity,
                        matrix=placement_matrix,
                    )

        # segments done

        if segments > 1:
            top_object = path_aggregate
        else:
            top_object = aggregate
        if self.parent_aggregate is not None:
            api.aggregate.assign_object(
                self.file,
                products=[top_object],
                relating_object=self.parent_aggregate,
            )
        else:
            assign_storey_byindex(self.file, top_object, self.building, self.level)

        return top_object
