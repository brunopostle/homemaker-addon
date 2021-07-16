import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Floor(BaseClass):
    """A floor filling a room or space"""

    def __init__(self, args={}):
        super().__init__(args)
        self.above = 0.02
        self.below = 0.2
        self.id = ""
        self.ifc = "IFCSLAB"
        self.inner = 0.08
        self.path = []
        self.type = "molior-floor"
        for arg in args:
            self.__dict__[arg] = args[arg]
        # FIXME implement not_if_stair_below

    def Ifc(self, ifc):
        """Generate some ifc"""
        entity = run(
            "root.create_entity",
            ifc,
            ifc_class=self.ifc,
            name=self.name,
        )
        ifc.assign_storey_byindex(entity, self.level)
        shape = ifc.createIfcShapeRepresentation(
            self.context,
            "Body",
            "SweptSolid",
            [
                ifc.createExtrudedAreaSolid(
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.below + self.above,
                )
            ],
        )
        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation - self.below], [1.0, 0.0, 0.0]
            ),
        )
