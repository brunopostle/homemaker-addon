import os
import sys
import ifcopenshell.api

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
        # FIXME set colour
        # if not cell.IsOutside():
        #    crinkliness = cell.Crinkliness()
        #    colour = (int(crinkliness*16)-7)*10
        #    if colour > 170: colour = 170
        #    if colour < 10: colour = 10

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
        except:
            is_external = False
        pset = run("pset.add_pset", ifc, product=entity, Name="Pset_SpaceCommon")
        run("pset.edit_pset", ifc, pset=pset, Properties={"IsExternal": is_external})

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
        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.floor], [1.0, 0.0, 0.0]
            ),
        )
