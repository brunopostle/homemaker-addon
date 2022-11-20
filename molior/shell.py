import ifcopenshell.api

from topologist.helpers import string_to_coor, el
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d, map_to_2d_simple, matrix_align
from molior.ifc import (
    add_face_topology_epsets,
    create_extruded_area_solid,
    create_curve_bounded_plane,
    create_face_surface,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
    get_type_object,
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
        self.party_wall = False
        self.layerset = [[0.03, "Plaster"], [0.2, "Insulation"], [0.05, "Tiles"]]
        self.structural_material = "Concrete"
        self.outer = 0.20
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]
        self.inner = self.thickness - self.outer

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
            name=self.name,
        )
        run(
            "geometry.edit_object_placement",
            self.file,
            product=aggregate,
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
            # need this for structure
            face_surface = create_face_surface(self.file, vertices, normal)
            for vertex in vertices:
                if elevation == None or vertex[2] < elevation:
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

            element = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.name,
            )
            if hasattr(element, "PredefinedType"):
                element.PredefinedType = self.predefined_type
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

            # TODO skip unless Pset_*Common.LoadBearing
            # generate structural surfaces
            structural_surface = run(
                "root.create_entity",
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
                    self.style_object,
                    name=self.structural_material,
                    stylename=self.style,
                ),
            )

            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [element]

            # reuse (or create) a Type
            product_type = get_type_object(
                self.file,
                self.style_object,
                ifc_type=self.ifc + "Type",
                stylename=self.style,
                name=self.name,
            )

            for association in product_type.HasAssociations:
                if association.is_a("IfcRelAssociatesMaterial"):
                    relating_material = association.RelatingMaterial
                    if relating_material.is_a("IfcMaterialLayerSetUsage"):
                        self.outer = -relating_material.OffsetFromReferenceLine
                    if relating_material.is_a("IfcMaterialLayerSet"):
                        self.thickness = 0.0
                        for material_layer in relating_material.MaterialLayers:
                            self.thickness += material_layer.LayerThickness
            self.inner = self.thickness - self.outer

            run(
                "type.assign_type",
                self.file,
                related_object=element,
                relating_type=product_type,
            )

            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)

            # create a representation
            if normal[2] < -0.999:
                extrude_height = self.thickness
                extrude_direction = [0.0, 0.0, -1.0]
                matrix = matrix @ matrix_align([0.0, 0.0, self.inner], [1.0, 0.0, 0.0])
            elif float(normal_x[2]) < 0.001 or not uniform_pitch:
                extrude_height = self.thickness
                extrude_direction = [0.0, 0.0, 1.0]
                matrix = matrix @ matrix_align([0.0, 0.0, -self.inner], [1.0, 0.0, 0.0])
            else:
                extrude_height = self.thickness / float(normal_x[2])
                extrude_direction = [
                    0.0,
                    0 - float(normal_x[1]),
                    float(normal_x[2]),
                ]
                matrix = matrix @ matrix_align(
                    [
                        0.0,
                        self.inner * float(normal_x[1]),
                        0.0 - (self.inner * float(normal_x[2])),
                    ],
                    [1.0, self.inner * float(normal_x[1]), 0.0],
                )
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
