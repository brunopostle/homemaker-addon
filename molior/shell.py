import ifcopenshell.api.aggregate
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.api.structural
import ifcopenshell.api.type
from topologist.helpers import string_to_coor, el
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d, map_to_2d_simple, matrix_align
from molior.ifc import (
    add_face_topology_epsets,
    create_extruded_area_solid,
    create_curve_bounded_plane,
    create_face_surface,
    assign_storey_byindex,
    get_type_object,
    get_thickness,
    get_material_by_name,
    get_context_by_name,
)

api = ifcopenshell.api


class Shell(BaseClass):
    """A pitched roof or soffit"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcRoof"
        self.party_wall = False
        self.structural_material = "Concrete"
        self.structural_thickness = 0.2
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference", target_view="GRAPH_VIEW"
        )
        body_context = get_context_by_name(self.file, context_identifier="Body")

        aggregate = api.root.create_entity(
            self.file,
            ifc_class="IfcElementAssembly",
            name=self.name,
        )
        api.geometry.edit_object_placement(
            self.file,
            product=aggregate,
        )

        inclines = []
        uniform_pitch = False
        for face in self.hull.faces:
            normal = face[1]["face"].Normal()
            inclines.append(normal[2])
        if len(inclines) > 1 and abs(max(inclines) - min(inclines)) < 0.01:
            uniform_pitch = True

        elevation = None
        for face in self.hull.faces:
            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]
            normal = face[1]["face"].Normal()
            # need this for structure
            face_surface = create_face_surface(self.file, vertices, normal)
            for vertex in vertices:
                if elevation is None or vertex[2] < elevation:
                    elevation = el(vertex[2])

            # skip if this is within a stair core
            if (
                face[1]["face"].IsHorizontal()
                and face[1]["back_cell"]
                and face[1]["back_cell"].Usage() == "stair"
                and face[1]["front_cell"]
                and face[1]["front_cell"].Usage() == "stair"
            ):
                self.ifc = "IfcVirtualElement"

            element = api.root.create_entity(
                self.file,
                ifc_class=self.ifc,
                name=self.name,
            )
            api.aggregate.assign_object(
                self.file,
                products=[element],
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
                    boundary = api.root.create_entity(
                        self.file,
                        ifc_class="IfcRelSpaceBoundary2ndLevel",
                    )

                    if mycell == face[1]["front_cell"]:
                        # the face points to this cell
                        nodes_2d, matrix = map_to_2d_simple(
                            reversed(vertices), [-v for v in normal]
                        )
                    else:
                        nodes_2d, matrix = map_to_2d_simple(vertices, normal)

                    curve_bounded_plane = create_curve_bounded_plane(
                        self.file, nodes_2d, matrix
                    )
                    boundary.ConnectionGeometry = (
                        self.file.createIfcConnectionSurfaceGeometry(
                            curve_bounded_plane
                        )
                    )
                    if element.is_a("IfcVirtualElement"):
                        boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                    else:
                        boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    if self.party_wall:
                        boundary.InternalOrExternalBoundary = "EXTERNAL_FIRE"
                    elif face[1]["face"].IsHorizontal() and not face[1][
                        "face"
                    ].CellBelow(self.cellcomplex):
                        boundary.InternalOrExternalBoundary = "EXTERNAL_EARTH"
                    elif face[1]["face"].IsInternal(self.cellcomplex):
                        boundary.InternalOrExternalBoundary = "INTERNAL"
                    else:
                        boundary.InternalOrExternalBoundary = "EXTERNAL"
                    boundary.RelatedBuildingElement = element

                    cell_index = mycell.Get("index")
                    if cell_index is not None:
                        # can't assign psets to an IfcRelationship, use Description instead
                        boundary.Description = "CellIndex " + str(cell_index)
                    face_index = face[1]["face"].Get("index")
                    if face_index is not None:
                        boundary.Name = "FaceIndex " + face_index

            if element.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # TODO skip unless Pset_*Common.LoadBearing
            # generate structural surfaces
            structural_surface = api.root.create_entity(
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.style + "/" + self.name,
                predefined_type="SHELL",
            )
            add_face_topology_epsets(
                self.file,
                structural_surface,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            structural_surface.Thickness = self.structural_thickness
            api.structural.assign_structural_analysis_model(
                self.file,
                product=structural_surface,
                structural_analysis_model=self.structural_analysis_model,
            )
            api.geometry.assign_representation(
                self.file,
                product=structural_surface,
                representation=self.file.createIfcTopologyRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Face",
                    [face_surface],
                ),
            )
            api.material.assign_material(
                self.file,
                products=[structural_surface],
                material=get_material_by_name(
                    self.file,
                    self.style_object,
                    name=self.structural_material,
                    stylename=self.style,
                ),
            )

            assignment = api.root.create_entity(self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [element]

            # type (IfcVirtualElementType isn't valid)

            product_type = get_type_object(
                self.file,
                self.style_object,
                ifc_type=self.ifc + "Type",
                stylename=self.style,
                name=self.name,
            )
            api.type.assign_type(
                self.file,
                related_objects=[element],
                relating_type=product_type,
            )

            thickness = get_thickness(self.file, product_type)
            inner = thickness + self.offset

            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)

            # create a representation
            if normal[2] < -0.999:
                extrude_height = thickness
                extrude_direction = [0.0, 0.0, -1.0]
                matrix = matrix @ matrix_align([0.0, 0.0, inner], [1.0, 0.0, 0.0])
            elif float(normal_x[2]) < 0.001 or not uniform_pitch:
                extrude_height = thickness
                extrude_direction = [0.0, 0.0, 1.0]
                matrix = matrix @ matrix_align([0.0, 0.0, -inner], [1.0, 0.0, 0.0])
            else:
                extrude_height = thickness / float(normal_x[2])
                extrude_direction = [
                    0.0,
                    0 - float(normal_x[1]),
                    float(normal_x[2]),
                ]
                matrix = matrix @ matrix_align(
                    [
                        0.0,
                        inner * float(normal_x[1]),
                        0.0 - (inner * float(normal_x[2])),
                    ],
                    [1.0, inner * float(normal_x[1]), 0.0],
                )

            # TODO use geometry.add_slab_representation
            shape = self.file.createIfcShapeRepresentation(
                body_context,
                body_context.ContextIdentifier,
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
            api.geometry.assign_representation(
                self.file,
                product=element,
                representation=shape,
            )
            api.geometry.edit_object_placement(
                self.file,
                product=element,
                matrix=matrix,
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
