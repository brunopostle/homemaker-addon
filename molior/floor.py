import ifcopenshell.api

from topologic import Face, Cell
from topologist.helpers import create_stl_list

from molior.baseclass import TraceClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Floor(TraceClass):
    """A floor filling a room or space"""

    def __init__(self, args={}):
        super().__init__(args)
        self.below = 0.2
        self.ifc = "IfcSlab"
        self.ifc_class = "IfcSlabType"
        self.predefined_type = "FLOOR"
        self.layerset = [[0.2, "Concrete"], [0.02, "Screed"]]
        self.path = []
        self.type = "molior-floor"
        for arg in args:
            self.__dict__[arg] = args[arg]
        # FIXME implement not_if_stair_below
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]

    def execute(self):
        """Generate some ifc"""
        entity = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.name,
        )

        myelement_type = self.get_element_type()
        run(
            "type.assign_type",
            self.file,
            related_object=entity,
            relating_type=myelement_type,
        )
        self.add_psets(myelement_type)

        string_coor_start = next(iter(self.chain.graph))
        cell = self.chain.graph[string_coor_start][1][3]
        if cell.__class__ == Cell:
            topology_index = cell.Get("index")
            self.add_pset(entity, "EPset_Topology", {"CellIndex": str(topology_index)})
            faces_bottom = create_stl_list(Face)
            cell.FacesBottom(faces_bottom)
            faces_bottom = [str(face.Get("index")) for face in list(faces_bottom)]
            self.add_pset(
                entity, "EPset_Topology", {"FaceIndices": " ".join(faces_bottom)}
            )

        # Usage isn't created until after type.assign_type
        mylayerset = ifcopenshell.util.element.get_material(myelement_type)
        for inverse in self.file.get_inverse(mylayerset):
            if inverse.is_a("IfcMaterialLayerSetUsage"):
                inverse.OffsetFromReferenceLine = 0.0 - self.below

        self.file.assign_storey_byindex(entity, self.level)
        shape = self.file.createIfcShapeRepresentation(
            self.context,
            "Body",
            "SweptSolid",
            [
                self.file.createExtrudedAreaSolid(
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.thickness,
                )
            ],
        )
        run(
            "geometry.assign_representation",
            self.file,
            product=entity,
            representation=shape,
        )
        run(
            "geometry.edit_object_placement",
            self.file,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation - self.below], [1.0, 0.0, 0.0]
            ),
        )
