import os
import sys
import ifcopenshell.api
import numpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import matrix_align
from topologic import Face
from topologist.helpers import create_stl_list

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

    def Ifc(self, ifc, context):
        """Generate some ifc"""
        # the cell is the first cell attached to any edge in the chain
        string_coor_start = next(iter(self.chain.graph))
        cell = self.chain.graph[string_coor_start][1][3]

        entity = run(
            "root.create_entity",
            ifc,
            ifc_class="IfcSpace",
            name=self.usage + "/" + str(cell.Get("index")),
        )

        try:
            is_external = cell.IsOutside()
            crinkliness = int(cell.Crinkliness() * 10) / 10
        except:
            is_external = False
            crinkliness = 1.0
        pset = run("pset.add_pset", ifc, product=entity, name="Pset_SpaceCommon")
        run("pset.edit_pset", ifc, pset=pset, properties={"IsExternal": is_external})

        ifc.assign_storey_byindex(entity, self.level)
        # simple extruded representation
        representation = ifc.createExtrudedAreaSolid(
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
            tessellation = ifc.createTessellation_fromMesh(vertices, faces)
            representation = ifc.createIfcBooleanResult(
                "INTERSECTION", representation, tessellation
            )
            representationtype = "CSG"

        shape = ifc.createIfcShapeRepresentation(
            context,
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
                ifc,
                name="Crinkliness " + str(crinkliness),
                surface_colour=[red, green, blue],
                diffuse_colour=[red, green, blue],
                transparency=0.5,
                external_definition=None,
            )
        else:
            style = run(
                "style.add_style",
                ifc,
                name="Outdoor Space",
                surface_colour=[1.0, 1.0, 1.0],
                diffuse_colour=[1.0, 1.0, 1.0],
                transparency=0.9,
                external_definition=None,
            )
        run(
            "style.assign_representation_styles",
            ifc,
            shape_representation=shape,
            styles=[style],
        )

        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.floor], [1.0, 0.0, 0.0]
            ),
        )
