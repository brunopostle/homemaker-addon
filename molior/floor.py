from topologic_core import Cell, CellComplex
import ifcopenshell.api.root

from .baseclass import TraceClass
from .geometry import matrix_align
from .ifc import (
    add_pset,
    add_cell_topology_epsets,
    create_closed_profile_from_points,
    assign_storey_byindex,
    get_thickness,
    get_type_object,
    get_context_by_name,
)

api = ifcopenshell.api


class Floor(TraceClass):
    """A floor filling a room or space"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.ifc = "IfcCovering"
        self.path = []
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""

        # contexts

        body_context = get_context_by_name(self.file, context_identifier="Body")

        # every node in the graph references the Topologic cell, pick one
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

        # create an element

        element = api.root.create_entity(
            self.file,
            ifc_class=self.ifc,
            name=self.name + "/" + str(cell.Get("index")),
        )

        # Will be re-assigned to Space later
        assign_storey_byindex(self.file, element, self.building, self.level)

        # topologic_core stuff

        if type(cell) == Cell:
            bottom_faces_ptr = []
            cell.FacesBottom(bottom_faces_ptr)

            if cell.Get("index") is not None:
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

        # representation

        if element.is_a("IfcVirtualElement"):
            return
        if not self.do_representation:
            return

        # type (IfcVirtualElementType isn't valid)

        type_product = get_type_object(
            self.file,
            self.style_object,
            ifc_type=self.ifc + "Type",
            stylename=self.style,
            name=self.typename,
        )
        api.type.assign_type(
            self.file,
            related_objects=[element],
            relating_type=type_product,
        )

        thickness = get_thickness(self.file, type_product)

        shape_representation = api.geometry.add_profile_representation(
            self.file,
            context=body_context,
            profile=create_closed_profile_from_points(
                self.file, [self.corner_in(index) for index in range(len(self.path))]
            ),
            depth=thickness,
        )

        api.geometry.assign_representation(
            self.file,
            product=element,
            representation=shape_representation,
        )
        api.geometry.edit_object_placement(
            self.file,
            product=element,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.offset], [1.0, 0.0, 0.0]
            ),
        )
