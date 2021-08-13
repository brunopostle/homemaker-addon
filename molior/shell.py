import ifcopenshell.api

from molior.baseclass import BaseClass
from molior.geometry import map_to_2d
from topologist.helpers import string_to_coor

run = ifcopenshell.api.run


class Shell(BaseClass):
    """A pitched roof or soffit"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ifc = "IfcRoof"
        self.ifc_class = "IfcRoofType"
        self.predefined_type = "USERDEFINED"
        self.layerset = [[0.03, "Plaster"], [0.2, "Insulation"], [0.05, "Tiles"]]
        self.inner = 0.08
        self.outer = 0.20
        self.type = "molior-shell"
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""
        # TODO aggregate entities
        for face in self.hull.faces:
            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]
            normal = face[1]
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)

            # TODO IfcRoof and IfcWall elements should generate IfcStructuralSurfaceMember
            entity = run(
                "root.create_entity", self.file, ifc_class=self.ifc, name=self.name
            )
            self.add_topology_pset(entity, *face[2])

            myelement_type = self.get_element_type()
            run(
                "type.assign_type",
                self.file,
                related_object=entity,
                relating_type=myelement_type,
            )
            self.add_psets(myelement_type)

            # Usage isn't created until after type.assign_type
            mylayerset = ifcopenshell.util.element.get_material(myelement_type)
            for inverse in self.file.get_inverse(mylayerset):
                if inverse.is_a("IfcMaterialLayerSetUsage"):
                    inverse.OffsetFromReferenceLine = 0.0 - self.inner

            # FIXME this puts roofs in the ground floor
            self.file.assign_storey_byindex(entity, 0)
            if abs(float(normal_x[2])) < 0.001:
                extrude_height = self.outer
                extrude_direction = [0.0, 0.0, 1.0]
            else:
                extrude_height = self.outer / float(normal_x[2])
                extrude_direction = [
                    0.0,
                    0 - float(normal_x[1]),
                    float(normal_x[2]),
                ]
            shape = self.file.createIfcShapeRepresentation(
                self.context,
                "Body",
                "SweptSolid",
                [
                    self.file.createExtrudedAreaSolid(
                        nodes_2d,
                        extrude_height,
                        extrude_direction,
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
                matrix=matrix,
            )
