import numpy as np
import ifcopenshell.api.root
import ifcopenshell.api.style

from .baseclass import TraceClass
from .geometry import matrix_align
from .ifc import (
    add_pset,
    add_cell_topology_epsets,
    create_extruded_area_solid,
    create_tessellation_from_mesh,
    assign_storey_byindex,
    get_context_by_name,
)

api = ifcopenshell.api


class Space(TraceClass):
    """A room or outside volume, as a 2D path extruded vertically"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ceiling = 0.2
        self.floor = 0.02
        self.ifc = "IfcSpace"
        self.predefined_type = "INTERNAL"
        self.inner = 0.08
        self.path = []
        self.usage = ""
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.usage = self.name

    def execute(self):
        """Generate some ifc"""
        body_context = get_context_by_name(self.file, context_identifier="Body")
        # the cell is the first cell attached to any edge in the chain
        cell = self.chain.graph[next(iter(self.chain.graph))][1]["back_cell"]

        element = api.root.create_entity(
            self.file,
            ifc_class=self.ifc,
            predefined_type=self.predefined_type,
            name=self.usage + "/" + str(cell.Get("index")),
        )

        try:
            is_external = cell.IsOutside()
            crinkliness = int(cell.Crinkliness(self.cellcomplex) * 10) / 10
        except AttributeError:
            is_external = False
            crinkliness = 1.0
        except RuntimeError:
            is_external = False
            crinkliness = 1.0
        separation = cell.Get("separation")
        if separation is not None:
            separation = float(separation)

        add_pset(
            self.file,
            element,
            "Pset_SpaceOccupancyRequirements",
            {"OccupancyType": self.condition},
        )
        add_pset(
            self.file,
            element,
            "EPset_Pattern",
            {"Crinkliness": crinkliness, "Separation": separation},
        )
        add_cell_topology_epsets(self.file, element, cell)

        self.add_psets(element)

        assign_storey_byindex(self.file, element, self.building, self.level)

        if not self.do_representation:
            return
        # simple extruded representation
        representation = create_extruded_area_solid(
            self.file,
            [self.corner_in(index) for index in range(len(self.path))],
            self.height - self.ceiling,
        )
        representationtype = "SweptSolid"

        # clip if original cell has non-horizontal ceiling
        faces_ptr = []
        cell.FacesInclined(faces_ptr)
        if len(faces_ptr) > 0:
            vertices, faces = cell.Mesh()
            vertices = [
                [v[0], v[1], v[2] - self.elevation - self.floor] for v in vertices
            ]
            tessellation = create_tessellation_from_mesh(self.file, vertices, faces)
            representation = self.file.createIfcBooleanResult(
                "INTERSECTION", representation, tessellation
            )
            representationtype = "CSG"

        shape = self.file.createIfcShapeRepresentation(
            body_context,
            body_context.ContextIdentifier,
            representationtype,
            [representation],
        )

        if not is_external:
            red = np.clip(1.0 - crinkliness, 0.0, 1.0)
            green = np.clip(crinkliness, 0.0, 1.0)
            blue = np.clip(crinkliness - 1.0, 0.0, 1.0)
            style = api.style.add_style(
                self.file, name="Crinkliness " + str(crinkliness)
            )
            api.style.add_surface_style(
                self.file,
                style=style,
                ifc_class="IfcSurfaceStyleShading",
                attributes={
                    "SurfaceColour": {
                        "Name": None,
                        "Red": red,
                        "Green": green,
                        "Blue": blue,
                    },
                    "Transparency": 0.5,
                },
            )
            # FIXME report 159 LIGHT ON TWO SIDES: custom psets? STDERR?
        else:
            style = api.style.add_style(self.file, name="Outside Space")
            api.style.add_surface_style(
                self.file,
                style=style,
                ifc_class="IfcSurfaceStyleShading",
                attributes={
                    "SurfaceColour": {
                        "Name": None,
                        "Red": 1.0,
                        "Green": 1.0,
                        "Blue": 1.0,
                    },
                    "Transparency": 0.9,
                },
            )
        api.style.assign_representation_styles(
            self.file,
            shape_representation=shape,
            styles=[style],
        )

        api.geometry.assign_representation(
            self.file,
            product=element,
            representation=shape,
        )
        api.geometry.edit_object_placement(
            self.file,
            product=element,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation + self.floor], [1.0, 0.0, 0.0]
            ),
        )
