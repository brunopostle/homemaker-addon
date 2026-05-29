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
from topologist.fitness.p105_south_facing_outdoors import Assessor as P105
from topologist.fitness.p107_wings_of_light import Assessor as P107
from topologist.fitness.p127_intimacy_gradient import Assessor as P127
from topologist.fitness.p128_indoor_sunlight import Assessor as P128
from topologist.fitness.p129_common_areas_at_the_heart import Assessor as P129
from topologist.fitness.p131_the_flow_through_rooms import Assessor as P131
from topologist.fitness.p133_staircase_as_a_stage import Assessor as P133
from topologist.fitness.p138_sleeping_to_the_east import Assessor as P138
from topologist.fitness.p145_bulk_storage import Assessor as P145
from topologist.fitness.p159_light_on_two_sides_of_every_room import Assessor as P159
from topologist.fitness.p190_ceiling_height_variety import Assessor as P190

api = ifcopenshell.api


class Space(TraceClass):
    """A room or outside volume, as a 2D path extruded vertically"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.ceiling = 0.2
        self.floor = 0.02
        self.ifc = "IfcSpace"
        self.predefined_type = "INTERNAL"
        self.inner = 0.08
        self.path = []
        self.usage = ""
        self.shortest_path_table = None
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
        except AttributeError:
            is_external = False
        except RuntimeError:
            is_external = False
        separation = cell.Get("separation")
        if separation is not None:
            separation = float(separation)

        if self.cellcomplex is not None and type(cell).__name__ == "Cell":
            assessors = [
                ("P105", P105(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P107", P107(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P127", P127(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P128", P128(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P129", P129(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P131", P131(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P133", P133(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P138", P138(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P145", P145(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P159", P159(self.cellcomplex, self.circulation, self.shortest_path_table)),
                ("P190", P190(self.cellcomplex, self.circulation, self.shortest_path_table)),
            ]
            pattern_scores = {key: round(a.execute(cell), 3) for key, a in assessors}
        else:
            pattern_scores = {
                key: 1.0
                for key in ["P105", "P107", "P127", "P128", "P129", "P131", "P133", "P138", "P145", "P159", "P190"]
            }
        pattern_scores["Separation"] = separation

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
            pattern_scores,
        )
        if type(cell).__name__ == "Cell":
            add_pset(
                self.file,
                element,
                "Qto_SpaceBaseQuantities",
                {
                    "NetFloorArea": self.file.createIfcAreaMeasure(cell.PlanArea()),
                    "NetVolume": self.file.createIfcVolumeMeasure(cell.Volume()),
                },
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
            p159_score = pattern_scores["P159"]
            red = np.clip(1.0 - p159_score, 0.0, 1.0)
            green = np.clip(p159_score, 0.0, 1.0)
            blue = np.clip(p159_score - 1.0, 0.0, 1.0)
            style = api.style.add_style(
                self.file, name="P159 " + str(p159_score)
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
