import os, sys, ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
import molior
from molior.geometry import add_2d, subtract_2d, scale_2d, distance_2d, matrix_align
from molior.extrusion import Extrusion

run = ifcopenshell.api.run


class Repeat(BaseClass):
    """A row of evenly spaced identical objects"""

    def __init__(self, args={}):
        super().__init__(args)
        self.alternate = 0
        self.closed = 0
        self.height = 0.0
        self.ifc = "IFCBUILDINGELEMENTPROXY"
        self.inset = 0.0
        self.xshift = 0.0
        self.yshift = 0.0
        self.outer = 0.08
        self.path = []
        self.spacing = 1.0
        self.traces = []
        self.type = "molior-repeat"
        self.Extrusion = Extrusion
        self.Repeat = Repeat
        for arg in args:
            self.__dict__[arg] = args[arg]

    def Ifc(self, ifc):
        """Generate some ifc"""
        style = molior.Molior.style
        myconfig = style.get(self.style)
        # FIXME should use alternative assets for different heights
        if self.asset in self.style_assets:
            dxf_path = style.get_file(
                self.style, self.style_assets[self.asset][0]["file"]
            )
        else:
            dxf_path = style.get_file(self.style, "error.dxf")

        segments = self.segments()
        self.outer += self.xshift

        for id_segment in range(segments):
            inset = scale_2d(self.direction_segment(id_segment), self.inset)
            # outside face start and end coordinates
            v_out_a = add_2d(self.corner_out(id_segment), inset)
            v_out_b = subtract_2d(self.corner_out(id_segment + 1), inset)
            # space to fill
            length = distance_2d(v_out_a, v_out_b)
            if self.spacing > 0.0 and self.spacing < length:
                items = int(length / self.spacing) + 1
            else:
                items = 2

            spacing = length / (items - 1)

            if self.alternate == 1:
                items -= 1
                v_out_a = add_2d(
                    v_out_a, scale_2d(self.direction_segment(id_segment), spacing / 2)
                )

            for index in range(items):
                if index > 0 or id_segment == 0 or self.inset > 0.0:
                    location = add_2d(
                        v_out_a,
                        scale_2d(self.direction_segment(id_segment), index * spacing),
                    )
                    entity = run(
                        "root.create_entity",
                        ifc,
                        ifc_class=self.ifc,
                        name=self.style + "/" + self.condition,
                    )
                    # place the entity in space
                    elevation = self.elevation + self.yshift
                    run(
                        "geometry.edit_object_placement",
                        ifc,
                        product=entity,
                        matrix=matrix_align(
                            [*location, elevation],
                            [
                                *add_2d(location, self.direction_segment(id_segment)),
                                elevation,
                            ],
                        ),
                    )
                    # assign the entity to a storey
                    ifc.assign_storey_byindex(entity, self.level)

                    # load geometry from a DXF file and assign to the entity
                    ifc.assign_representation_fromDXF(
                        self.context, entity, self.style, dxf_path
                    )

                # fill space between
                if index == items - 1:
                    continue
                for condition in self.traces:
                    for name in myconfig["traces"]:
                        if name == condition:
                            config = myconfig["traces"][name]
                            vals = {
                                "closed": 0,
                                "path": [
                                    location,
                                    add_2d(
                                        location,
                                        scale_2d(
                                            self.direction_segment(id_segment), spacing
                                        ),
                                    ),
                                ],
                                "context": self.context,
                                "name": name,
                                "elevation": self.elevation,
                                "height": self.height,
                                "xshift": self.xshift,
                                "yshift": self.yshift,
                                "normals": self.normals,
                                "normal_set": self.normal_set,
                                "style": self.style,
                                "level": self.level,
                                "style_assets": self.style_assets,
                            }
                            vals.update(config)
                            part = getattr(self, config["class"])(vals)

                            part.Ifc(ifc)
