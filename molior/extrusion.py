import ifcopenshell.api

import molior
from molior.baseclass import TraceClass
from molior.geometry import matrix_align, add_2d

run = ifcopenshell.api.run


class Extrusion(TraceClass):
    """A profile following a horizontal 2D path"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ifc = "IfcBuildingElementProxy"
        self.predefined_type = "USERDEFINED"
        self.closed = 0
        self.extension = 0.0
        self.scale = 1.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.path = []
        self.type = "molior-extrusion"
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        style = molior.Molior.style
        """Generate some ifc"""
        entity = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.name,
            predefined_type=self.predefined_type,
        )
        # TODO IfcBeam elements should generate IfcStructuralCurveMember
        # TODO assign materials
        self.file.assign_storey_byindex(entity, self.level)
        directrix = self.path
        if self.closed:
            directrix.append(directrix[0])
        else:
            # FIXME need to terminate with a mitre when continuation is in another style
            # FIXME clip negative extension to segment length
            directrix[0] = add_2d(directrix[0], self.extension_start())
            directrix[-1] = add_2d(directrix[-1], self.extension_end())

        dxf_path = style.get_file(self.style, self.profile)

        transform = self.file.createIfcCartesianTransformationOperator2D(
            None,
            None,
            self.file.createIfcCartesianPoint([self.yshift, self.xshift]),
            self.scale,
        )

        self.file.assign_extrusion_fromDXF(
            self.context,
            entity,
            directrix,
            self.style,
            dxf_path,
            transform,
        )

        run(
            "geometry.edit_object_placement",
            self.file,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.height], [1.0, 0.0, 0.0]
            ),
        )
