import ifcopenshell.api

from topologic import Cell, CellComplex

from molior.baseclass import TraceClass
from molior.geometry import matrix_align
from molior.ifc import (
    add_pset,
    add_cell_topology_epsets,
    create_extruded_area_solid,
    assign_storey_byindex,
    get_context_by_name,
)

run = ifcopenshell.api.run


class Floor(TraceClass):
    """A floor filling a room or space"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.below = 0.0
        self.ifc = "IfcCovering"
        self.predefined_type = "FLOORING"
        self.layerset = [[0.02, "Tiles"]]
        self.path = []
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]

    def execute(self):
        """Generate some ifc"""
        body_context = get_context_by_name(self.file, context_identifier="Body")

        # every node in the graph references the cell, pick one
        cell = self.chain.graph[next(iter(self.chain.graph))][1]["back_cell"]

        # skip if part of a stair core
        if (
            type(cell) == Cell
            and type(self.cellcomplex) == CellComplex
            and cell.Usage() == "stair"
        ):
            below_cells_ptr = []
            cell.CellsBelow(self.cellcomplex, below_cells_ptr)
            for cell_below in below_cells_ptr:
                if cell_below.Usage() == "stair":
                    return

        element = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.name + "/" + str(cell.Get("index")),
        )
        if hasattr(element, "PredefinedType"):
            element.PredefinedType = self.predefined_type
        # Will be re-assigned to Space later
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
