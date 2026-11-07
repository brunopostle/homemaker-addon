import numpy as np
import ifcopenshell.api.attribute
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.structural

from topologic_core import Face, Vertex
from .baseclass import BaseClass
from .geometry import map_to_2d, add_2d, scale_2d, subtract_3d, inset_path
from .ifc import (
    add_face_topology_epsets,
    assign_storey_byindex,
    assign_structural_profile,
    get_context_by_name,
    get_type_object,
    is_load_bearing,
)
from .extrusion import Extrusion
from .repeat import Repeat
from .shell import Shell

try:
    from topologist import hulls
    from topologist.helpers import string_to_coor, el
except ImportError:
    from ..topologist import hulls
    from ..topologist.helpers import string_to_coor, el

api = ifcopenshell.api


def transform_structural_members(members, matrix):
    """Move Structural Curve Members drawn in the coordinates of a Face to where it is"""
    for member in members:
        edge = member.Representation.Representations[0].Items[0]
        for vertex in (edge.EdgeStart, edge.EdgeEnd):
            point = vertex.VertexGeometry
            point.Coordinates = [
                float(value) for value in (matrix @ [*point.Coordinates, 1.0])[0:3]
            ]
        member.Axis.DirectionRatios = [
            float(value) for value in matrix[0:3, 0:3] @ member.Axis.DirectionRatios
        ]


class Grillage(BaseClass):
    """planar feature consisting of repeated linear elements"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.spacing = 0.45
        self.angle = 90.0
        self.do_levelling = False
        self.ifc = "IfcElementAssembly"
        self.traces = []
        self.hulls = []
        self.Extrusion = Extrusion
        self.Repeat = Repeat
        self.Shell = Shell
        self.Grillage = Grillage
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""

        myconfig = self.style_object.get(self.style)

        aggregate = api.root.create_entity(
            self.file,
            ifc_class=self.ifc,
            name=self.name,
        )
        api.geometry.edit_object_placement(
            self.file,
            product=aggregate,
        )

        self.structural_members = []
        elevation = None
        for face in self.hull.faces:
            # grillages are mapped from above
            if face[1]["face"].IsUpward() or face[1]["face"].IsVertical():
                normal = face[1]["face"].Normal()
            else:
                normal = subtract_3d([0.0, 0.0, 0.0], face[1]["face"].Normal())

            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]

            # need this for boundaries
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)

            # levelling
            ref_direction = None
            if self.do_levelling:
                ref_direction = [float(normal_x[2]), -float(normal_x[1])]

            for vertex in vertices:
                if elevation is None or vertex[2] < elevation:
                    elevation = el(vertex[2])

            face_aggregate = api.root.create_entity(
                self.file,
                ifc_class=self.ifc,
                name=self.name,
            )
            api.aggregate.assign_object(
                self.file,
                products=[face_aggregate],
                relating_object=aggregate,
            )
            add_face_topology_epsets(
                self.file,
                face_aggregate,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            api.geometry.edit_object_placement(
                self.file,
                product=face_aggregate,
            )

            if face_aggregate.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # structural members made for this face, in the coordinates of the face
            face_members = []

            # generate repeating grillage elements

            points = inset_path(nodes_2d, inset=self.inset)
            if len(points) < 3:
                continue

            # create a Topologic Face for slicing
            topologic_face = Face.ByVertices(
                [Vertex.ByCoordinates(*node, 0.0) for node in points]
            )
            cropped_faces, cropped_edges = topologic_face.ParallelSlice(
                self.spacing, np.deg2rad(self.angle)
            )

            # recursively process cropped faces

            if self.hulls:
                cropped_hulls = hulls.Hulls()
                for cropped_face in cropped_faces:
                    cropped_hulls.add_face(
                        self.name,
                        self.style,
                        face=cropped_face,
                        front_cell=None,
                        back_cell=None,
                    )
                cropped_hulls.process()
                myhull = cropped_hulls.hulls[self.name][self.style]

                for condition in self.hulls:
                    for name in myconfig["hulls"]:
                        if name == condition:
                            config = myconfig["hulls"][name]
                            vals = {
                                "cellcomplex": self.cellcomplex,
                                "elevations": self.elevations,
                                "file": self.file,
                                "building": self.building,
                                # the infill between the lines isn't structure
                                "structural_analysis_model": (
                                    self.structural_analysis_model
                                    if config["class"] == "Grillage"
                                    else None
                                ),
                                "name": name,
                                "normals": self.normals,
                                "normal_set": self.normal_set,
                                "parent_aggregate": face_aggregate,
                                "style": self.style,
                                "hull": myhull[0],
                                "style_families": self.style_families,
                                "style_object": self.style_object,
                            }
                            vals.update(config)
                            part = getattr(self, config["class"])(vals)
                            part.execute()
                            if config["class"] == "Grillage":
                                face_members.extend(part.structural_members)

            # multiple linear elements on this Face

            for cropped_edge in cropped_edges:
                start = cropped_edge.StartVertex().Coordinates()
                end = cropped_edge.EndVertex().Coordinates()
                direction = cropped_edge.NormalisedVector()
                length = cropped_edge.Length()

                # draw from left to right, bottom to top

                if (abs(direction[0]) < 0.00001 and direction[1] < 0.0) or direction[
                    0
                ] < 0.0:
                    start, end = end, start
                    direction = [-direction[0], -direction[1], -direction[2]]

                # edges are drawn with traces

                for condition in self.traces:
                    for name in myconfig["traces"]:
                        if name == condition:
                            config = myconfig["traces"][name]
                            vals = {
                                "cellcomplex": self.cellcomplex,
                                "closed": False,
                                "path": [
                                    list(start[0:2]),
                                    add_2d(
                                        start,
                                        scale_2d(
                                            direction,
                                            length,
                                        ),
                                    ),
                                ],
                                "ref_direction": ref_direction,
                                "file": self.file,
                                "name": name,
                                "elevation": self.elevation,
                                "normals": self.normals,
                                "normal_set": self.normal_set,
                                "parent_aggregate": face_aggregate,
                                "style": self.style,
                                "building": self.building,
                                "structural_analysis_model": self.structural_analysis_model,
                                "level": self.level,
                                "style_families": self.style_families,
                                "style_object": self.style_object,
                            }
                            vals.update(config)
                            part = getattr(self, config["class"])(vals)
                            element = part.execute()
                            if (
                                self.structural_analysis_model is not None
                                and (
                                    element.is_a("IfcMember") or element.is_a("IfcBeam")
                                )
                                and is_load_bearing(
                                    get_type_object(
                                        self.file,
                                        self.style_object,
                                        ifc_type=part.ifc + "Type",
                                        stylename=part.style,
                                        name=part.typename,
                                    )
                                )
                            ):
                                face_members.append(
                                    self.add_curve_member(
                                        part,
                                        element,
                                        face,
                                        [*start[0:2], 0.0],
                                        [
                                            *add_2d(start, scale_2d(direction, length)),
                                            0.0,
                                        ],
                                    )
                                )

            # members of this face, and of grillages within it, move with it
            transform_structural_members(face_members, matrix)
            self.structural_members.extend(face_members)

            api.geometry.edit_object_placement(
                self.file,
                product=face_aggregate,
                matrix=matrix,
                should_transform_children=True,
            )

        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        if self.parent_aggregate is not None:
            api.aggregate.assign_object(
                self.file,
                products=[aggregate],
                relating_object=self.parent_aggregate,
            )
        else:
            assign_storey_byindex(self.file, aggregate, self.building, level)

    def add_curve_member(self, part, element, face, start, end):
        """A Structural Curve Member for a linear Element drawn by a trace, from
        start to end in the coordinates of the face, with the face normal as Axis"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference", target_view="GRAPH_VIEW"
        )
        structural_member = api.root.create_entity(
            self.file,
            ifc_class="IfcStructuralCurveMember",
            name=part.style + "/" + part.name,
            predefined_type="RIGID_JOINED_MEMBER",
        )
        api.structural.assign_product(
            self.file,
            relating_product=structural_member,
            related_object=element,
        )
        add_face_topology_epsets(
            self.file,
            structural_member,
            face[1]["face"],
            face[1]["back_cell"],
            face[1]["front_cell"],
        )
        structural_member.Axis = self.file.createIfcDirection([0.0, 0.0, 1.0])
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
                ifc_type=part.ifc + "Type",
                stylename=part.style,
                name=part.typename,
            ),
            self.style_object,
            stylename=part.style,
            profile=part.structural_profile,
            material=part.structural_material,
            default_profile=[
                "IfcRectangleProfileDef",
                {"ProfileType": "AREA", "XDim": 0.2, "YDim": 0.3},
            ],
        )
        return structural_member
