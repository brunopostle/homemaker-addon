import ifcopenshell.api
import numpy

from topologist.helpers import string_to_coor, el
from topologic import Face, Vertex
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d, add_2d, scale_2d, subtract_3d
from molior.ifc import (
    add_face_topology_epsets,
    create_face_surface,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
)
from molior.extrusion import Extrusion
from molior.repeat import Repeat
from molior.shell import Shell
import topologist.hulls

run = ifcopenshell.api.run


class Grillage(BaseClass):
    """planar feature consisting of repeated linear elements"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.structural_material = "Concrete"
        self.spacing = 0.45
        self.angle = 90.0
        self.do_levelling = False
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

        # contexts

        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )

        myconfig = self.style_object.get(self.style)

        aggregate = run(
            "root.create_entity",
            self.file,
            ifc_class="IfcElementAssembly",
            name=self.name,
        )
        run(
            "geometry.edit_object_placement",
            self.file,
            product=aggregate,
        )

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

            # need this for structure
            face_surface = create_face_surface(self.file, vertices, normal)
            for vertex in vertices:
                if elevation == None or vertex[2] < elevation:
                    elevation = el(vertex[2])

            face_aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcElementAssembly",
                name=self.name,
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
            run(
                "geometry.edit_object_placement",
                self.file,
                product=face_aggregate,
            )

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
                name=self.style + self.name,
                predefined_type="SHELL",
            )
            add_face_topology_epsets(
                self.file,
                structural_surface,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            structural_surface.Thickness = 0.2
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
                    self.style_object,
                    name=self.structural_material,
                    stylename=self.style,
                ),
            )

            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [face_aggregate]

            # generate repeating grillage elements

            # create a Topologic Face for slicing
            topologic_face = Face.ByVertices(
                [Vertex.ByCoordinates(*node, 0.0) for node in nodes_2d]
            )
            cropped_faces, cropped_edges = topologic_face.ParallelSlice(
                self.spacing, numpy.deg2rad(self.angle)
            )

            # recursively process cropped faces

            if self.hulls:
                cropped_hulls = topologist.hulls.Hulls()
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
                                "structural_analysis_model": self.structural_analysis_model,
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
                            part.execute()

            run(
                "geometry.edit_object_placement",
                self.file,
                product=face_aggregate,
                matrix=matrix,
                should_transform_children=True,
            )

        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        if self.parent_aggregate != None:
            run(
                "aggregate.assign_object",
                self.file,
                product=aggregate,
                relating_object=self.parent_aggregate,
            )
        else:
            assign_storey_byindex(self.file, aggregate, self.building, level)
