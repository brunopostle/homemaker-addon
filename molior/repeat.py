import ifcopenshell.api

from molior.baseclass import TraceClass
import molior
from molior.geometry import add_2d, subtract_2d, scale_2d, distance_2d, matrix_align
from molior.extrusion import Extrusion

run = ifcopenshell.api.run


class Repeat(TraceClass):
    """A row of evenly spaced identical objects"""

    def __init__(self, args={}):
        super().__init__(args)
        self.alternate = 0
        self.closed = 0
        self.height = 0.0
        self.ceiling = 0.0
        self.ifc = "IfcBuildingElementProxy"
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

    def execute(self):
        """Generate some ifc"""
        style = molior.Molior.style
        myconfig = style.get(self.style)
        if self.asset in self.style_assets:
            for index in range(len(self.style_assets[self.asset])):
                height = self.style_assets[self.asset][index]["height"]
                if height >= self.height - self.ceiling:
                    break
            dxf_path = style.get_file(
                self.style, self.style_assets[self.asset][index]["file"]
            )
        else:
            dxf_path = style.get_file(self.style, "error.dxf")

        segments = self.segments()
        self.outer += self.xshift

        for id_segment in range(segments):
            # FIXME implement not_start, not_end and not_corners
            # FIXME large inset can result in a negative length
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

            aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.style + "/" + self.condition,
            )
            # assign the aggregate to a storey
            self.file.assign_storey_byindex(aggregate, self.level)

            for index in range(items):
                if (
                    index > 0
                    or (id_segment == 0 and not self.closed)
                    or self.inset > 0.0
                ):
                    location = add_2d(
                        v_out_a,
                        scale_2d(self.direction_segment(id_segment), index * spacing),
                    )
                    # TODO IfcColumn elements should generate IfcStructuralCurveMember
                    entity = run(
                        "root.create_entity",
                        self.file,
                        ifc_class=self.ifc,
                        name=self.style + "/" + self.condition,
                    )
                    self.add_psets(entity)
                    # place the entity in space
                    elevation = self.elevation + self.yshift
                    run(
                        "geometry.edit_object_placement",
                        self.file,
                        product=entity,
                        matrix=matrix_align(
                            [*location, elevation],
                            [
                                *add_2d(location, self.direction_segment(id_segment)),
                                elevation,
                            ],
                        ),
                    )
                    # assign the entity to the aggregate
                    run(
                        "aggregate.assign_object",
                        self.file,
                        product=entity,
                        relating_object=aggregate,
                    )
                    # load geometry from a DXF file and assign to the entity
                    self.file.assign_representation_fromDXF(
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
                                "file": self.file,
                                "name": name,
                                "elevation": self.elevation,
                                "height": self.height - self.yshift,
                                "ceiling": self.ceiling,
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

                            part.execute()
