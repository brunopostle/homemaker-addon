import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Ceiling(BaseClass):
    """A ceiling filling a room or space"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ceiling = 0.2
        self.id = ""
        self.ifc = "IFCSLAB"
        self.inner = 0.08
        self.path = []
        self.type = "molior-ceiling"
        for arg in args:
            self.__dict__[arg] = args[arg]
        # FIXME implement not_if_stair_above
        # FIXME don't draw ceiling when roof forms the ceiling

    def Ifc(self, ifc, context):
        """Generate some ifc"""
        entity = run("root.create_entity", ifc, ifc_class="IfcSlab", name="Ceiling")
        ifc.assign_storey_byindex(entity, self.level)
        # TODO previous Molior module had Beams() method that drew a slab as parallel beams
        # which could be created as an IFC boolean intersection.
        # TODO draw surface for structure and boundary
        shape = ifc.createIfcShapeRepresentation(
            context,
            "Body",
            "SweptSolid",
            [
                ifc.createExtrudedAreaSolid(
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.ceiling,
                )
            ],
        )
        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.height - self.ceiling], [1.0, 0.0, 0.0]
            ),
        )
