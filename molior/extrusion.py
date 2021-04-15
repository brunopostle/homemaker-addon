import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior
from molior.baseclass import BaseClass
from molior.geometry_2d import matrix_align

run = ifcopenshell.api.run


class Extrusion(BaseClass):
    """A profile following a horizontal 2D path"""

    def __init__(self, args={}):
        super().__init__(args)
        self.closed = 0
        self.extension = 0.0
        self.path = []
        self.type = "molior-extrusion"
        for arg in args:
            self.__dict__[arg] = args[arg]

    def Ifc(self, ifc, context):
        style = molior.Molior.style
        """Generate some ifc"""
        entity = run(
            "root.create_entity",
            ifc,
            ifc_class=self.ifc,
            name="My Extrusion"
        )
        ifc.assign_storey_byindex(entity, self.level)

        directrix = self.path
        if self.closed:
            directrix.append(directrix[0])

        dxf_path = style.get_file(self.style, self.profile)

        ifc.assign_extrusion_fromDXF(
            context,
            entity,
            directrix,
            self.style,
            dxf_path,
        )

        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.height], [1.0, 0.0, 0.0]
            ),
        )
