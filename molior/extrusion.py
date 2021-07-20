import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import molior
from molior.baseclass import BaseClass
from molior.geometry import matrix_align, add_2d

run = ifcopenshell.api.run


class Extrusion(BaseClass):
    """A profile following a horizontal 2D path"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ifc = "IFCBUILDINGELEMENTPROXY"
        self.closed = 0
        self.extension = 0.0
        self.scale = 1.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.path = []
        self.type = "molior-extrusion"
        for arg in args:
            self.__dict__[arg] = args[arg]

    def Ifc(self, ifc):
        style = molior.Molior.style
        """Generate some ifc"""
        entity = run("root.create_entity", ifc, ifc_class=self.ifc, name=self.name)
        # TODO IfcRoof may be .FREEFORM. IfcBeam may have structural
        # attributes. IfcBuildingElementProxy can be .ELEMENT.
        ifc.assign_storey_byindex(entity, self.level)
        directrix = self.path
        if self.closed:
            directrix.append(directrix[0])
        else:
            # FIXME need to terminate with a mitre when continuation is in another style
            # FIXME clip negative extension to segment length
            directrix[0] = add_2d(directrix[0], self.extension_start())
            directrix[-1] = add_2d(directrix[-1], self.extension_end())

        dxf_path = style.get_file(self.style, self.profile)

        transform = ifc.createIfcCartesianTransformationOperator2D(
            None,
            None,
            ifc.createIfcCartesianPoint([self.yshift, self.xshift]),
            self.scale,
        )

        ifc.assign_extrusion_fromDXF(
            self.context,
            entity,
            directrix,
            self.style,
            dxf_path,
            transform,
        )

        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.height], [1.0, 0.0, 0.0]
            ),
        )
