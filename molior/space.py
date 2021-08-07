import ifcopenshell.api
import numpy

from topologic import Face
from topologist.helpers import create_stl_list
from molior.baseclass import TraceClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Space(TraceClass):
    """A room or outdoor volume, as a 2D path extruded vertically"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ceiling = 0.2
        self.colour = 255
        self.floor = 0.02
        self.ifc = "IfcSpace"
        self.inner = 0.08
        self.path = []
        self.type = "molior-space"
        self.usage = ""
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.usage = self.name

    def execute(self):
        """Generate some ifc"""
        # the cell is the first cell attached to any edge in the chain
        string_coor_start = next(iter(self.chain.graph))
        cell = self.chain.graph[string_coor_start][1][3]

        entity = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.usage + "/" + str(cell.Get("index")),
        )

        try:
            is_external = cell.IsOutside()
            crinkliness = int(cell.Crinkliness() * 10) / 10
        except:
            is_external = False
            crinkliness = 1.0
        self.add_pset(entity, "Custom_Pset", {"Crinkliness": str(crinkliness)})

        # FIXME should create IfcSpaceType for this
        self.add_psets(entity)

        self.file.assign_storey_byindex(entity, self.level)
        # simple extruded representation
        representation = self.file.createExtrudedAreaSolid(
            [self.corner_in(index) for index in range(len(self.path))],
            self.height - self.ceiling,
        )
        representationtype = "SweptSolid"

        # clip if original cell has non-horizontal ceiling
        faces_stl = create_stl_list(Face)
        cell.FacesInclined(faces_stl)
        if len(faces_stl) > 0:
            vertices, faces = cell.Mesh()
            vertices = [
                [v[0], v[1], v[2] - self.elevation - self.floor] for v in vertices
            ]
            tessellation = self.file.createTessellation_fromMesh(vertices, faces)
            representation = self.file.createIfcBooleanResult(
                "INTERSECTION", representation, tessellation
            )
            representationtype = "CSG"

        shape = self.file.createIfcShapeRepresentation(
            self.context,
            "Body",
            representationtype,
            [representation],
        )

        if not is_external:
            red = numpy.clip(1.0 - crinkliness, 0.0, 1.0)
            green = numpy.clip(crinkliness, 0.0, 1.0)
            blue = numpy.clip(crinkliness - 1.0, 0.0, 1.0)
            style = run(
                "style.add_style",
                self.file,
                name="Crinkliness " + str(crinkliness),
                surface_colour=[red, green, blue],
                diffuse_colour=[red, green, blue],
                transparency=0.5,
                external_definition=None,
            )
            # FIXME report 159 LIGHT ON TWO SIDES: custom psets? STDERR? IfcConstraint?
        else:
            style = run(
                "style.add_style",
                self.file,
                name="Outdoor Space",
                surface_colour=[1.0, 1.0, 1.0],
                diffuse_colour=[1.0, 1.0, 1.0],
                transparency=0.9,
                external_definition=None,
            )
        run(
            "style.assign_representation_styles",
            self.file,
            shape_representation=shape,
            styles=[style],
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
                [0.0, 0.0, self.elevation + self.floor], [1.0, 0.0, 0.0]
            ),
        )
