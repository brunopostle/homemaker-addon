import ifcopenshell.api

from topologic import Cell, CellComplex

from molior.baseclass import TraceClass
from molior.geometry import matrix_align, map_to_2d
from molior.ifc import (
    add_pset,
    add_face_topology_epsets,
    add_cell_topology_epsets,
    create_extruded_area_solid,
    create_curve_bounded_plane,
    create_face_surface,
    assign_storey_byindex,
    get_material_by_name,
)

run = ifcopenshell.api.run


class Floor(TraceClass):
    """A floor filling a room or space"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.below = 0.2
        self.ifc = "IfcSlab"
        self.predefined_type = "FLOOR"
        self.layerset = [[0.2, "Concrete"], [0.02, "Screed"]]
        self.structural_material = "Concrete"
        self.path = []
        self.type = "molior-floor"
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]

    def execute(self):
        """Generate some ifc"""
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Reference":
                reference_context = item
            if item.ContextIdentifier == "Body":
                body_context = item

        # every node in the graph references the cell, pick one
        cell = self.chain.graph[next(iter(self.chain.graph))][1]["back_cell"]

        # with stairs we want a Virtual Element instead of a Slab
        if (
            type(cell) == Cell
            and type(self.cellcomplex) == CellComplex
            and cell.Get("usage") == "stair"
        ):
            below_cells_ptr = []
            cell.CellsBelow(self.cellcomplex, below_cells_ptr)
            for cell_below in below_cells_ptr:
                if cell_below.Get("usage") == "stair":
                    self.ifc = "IfcVirtualElement"
                    break

        element = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.name + "/" + str(cell.Get("index")),
        )
        # Slab will be re-assigned to Space later
        assign_storey_byindex(self.file, element, self.building, self.level)

        if type(cell) == Cell:
            bottom_faces_ptr = []
            cell.FacesBottom(bottom_faces_ptr)

            # topology stuff
            if cell.Get("index") != None:
                add_cell_topology_epsets(self.file, element, cell)
                add_pset(
                    self.file,
                    element,
                    "EPset_Topology",
                    {
                        "FaceIndices": " ".join(
                            [str(face.Get("index")) for face in bottom_faces_ptr]
                        )
                    },
                )
            for face in bottom_faces_ptr:
                perimeter_vertices_ptr = []
                face.VerticesPerimeter(perimeter_vertices_ptr)
                vertices = [v.Coordinates() for v in perimeter_vertices_ptr]
                normal = face.Normal()
                # need this for boundaries
                nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
                # need this for structure
                face_surface = create_face_surface(self.file, vertices, normal)

                # generate space boundaries
                curve_bounded_plane = create_curve_bounded_plane(
                    self.file, nodes_2d, matrix
                )
                for cell in face.CellsOrdered(self.cellcomplex):
                    if cell == None:
                        continue
                    boundary = run(
                        "root.create_entity",
                        self.file,
                        ifc_class="IfcRelSpaceBoundary2ndLevel",
                    )
                    boundary.ConnectionGeometry = (
                        self.file.createIfcConnectionSurfaceGeometry(
                            curve_bounded_plane
                        )
                    )
                    boundary.RelatedBuildingElement = element
                    if element.is_a("IfcVirtualElement"):
                        boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                    else:
                        boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    if face.IsInternal(self.cellcomplex):
                        boundary.InternalOrExternalBoundary = "INTERNAL"
                    else:
                        boundary.InternalOrExternalBoundary = "EXTERNAL"
                    cell_index = cell.Get("index")
                    if cell_index != None:
                        # can't assign psets to an IfcRelationship, use Description instead
                        boundary.Description = "CellIndex " + cell_index

                # don't generate structural surfaces if this is only a boundary between cells
                if element.is_a("IfcVirtualElement"):
                    continue
                structural_surface = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcStructuralSurfaceMember",
                    name=self.name,
                    predefined_type="SHELL",
                )
                structural_surface.Thickness = self.thickness

                assignment = run(
                    "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
                )
                assignment.RelatingProduct = structural_surface
                assignment.RelatedObjects = [element]

                add_face_topology_epsets(
                    self.file,
                    structural_surface,
                    face,
                    *face.CellsOrdered(self.cellcomplex)
                )
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

        if element.is_a("IfcVirtualElement"):
            return
        if not self.do_representation:
            return
        # assign a type and place a representation
        myelement_type = self.get_element_type()
        run(
            "type.assign_type",
            self.file,
            related_object=element,
            relating_type=myelement_type,
        )
        self.add_psets(myelement_type)
        for inverse in self.file.get_inverse(
            ifcopenshell.util.element.get_material(myelement_type)
        ):
            if inverse.is_a("IfcMaterialLayerSetUsage"):
                inverse.OffsetFromReferenceLine = 0.0 - self.below

        shape = self.file.createIfcShapeRepresentation(
            body_context,
            body_context.ContextIdentifier,
            "SweptSolid",
            [
                create_extruded_area_solid(
                    self.file,
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.thickness,
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
            matrix=matrix_align(
                [0.0, 0.0, self.elevation - self.below], [1.0, 0.0, 0.0]
            ),
        )
