import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Space(BaseClass):
    """A room or outdoor volume, as a 2D path extruded vertically"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ceiling = 0.2
        self.colour = 255
        self.floor = 0.02
        self.id = ""
        self.ifc = "IFCSPACE"
        self.inner = 0.08
        self.path = []
        self.type = "molior-space"
        self.usage = ""
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.usage = self.name
        # FIXME identify cell and set colour
        # if not cell.IsOutside():
        #    crinkliness = cell.Crinkliness()
        #    colour = (int(crinkliness*16)-7)*10
        #    if colour > 170: colour = 170
        #    if colour < 10: colour = 10
        # FIXME cell[index] can be used for id
        # FIXME space may be bounded by roof

    def Ifc(self, ifc, context):
        """Generate some ifc"""
        entity = run("root.create_entity", ifc, ifc_class="IfcSpace", name=self.usage)
        ifc.assign_storey_byindex(entity, self.level)
        shape = ifc.createIfcShapeRepresentation(
            context,
            "Body",
            "SweptSolid",
            [
                ifc.createExtrudedAreaSolid(
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.height - self.ceiling,
                )
            ],
        )
        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        # TODO space may be .INTERNAL. or .EXTERNAL.
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.floor], [1.0, 0.0, 0.0]
            ),
        )
