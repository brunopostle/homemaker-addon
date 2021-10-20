"""Molior builds 3D models from topologist 'traces' and 'hulls'

Traces are 2D closed or open chains that define building elements,
differentiated by elevation, height and style properties, typically
running in an anti-clockwise direction, these follow the outlines of
rooms, walls, eaves, string-courses etc.

Hulls are 3D polygon meshes that define building elements
differentiated by style and orientation, these describe roofs, soffits
and other elements that can't be described by 'traces'.

Which traces and hulls are used, and how they are used, are defined by
files in the 'molior/style/share' folder and subfolders.  Each
subfolder has a unique name and represents a different architectural
'style', buildings can be all one style or have multiple styles, each
applied to different parts of the building.  Styles are inherited from
parent folders, and can represent only minor variations, without
needing to duplicate anything that is already defined by the parent
folder(s).  Access to these style definitions is handled by the
molior.style module.

Molior uses IfcOpenShell to generate IFC models of buildings, with
some extra helper methods defined in the molior.ifc module.  Different
building parts need to be constructed differently, so walls, floors,
extrusions etc. are each handled by dedicated modules.

Molior is largely derived from the Perl 'Molior' module, but has been
rewritten in python in order to interface with Topologic and
IfcOpenShell.

"""

import re
import ifcopenshell.util
from molior.extrusion import Extrusion
from molior.floor import Floor
from molior.shell import Shell
from molior.space import Space
from molior.stair import Stair
from molior.wall import Wall
from molior.repeat import Repeat

from molior.style import Style
from molior.geometry import subtract_3d, x_product_3d
from molior.ifc import (
    assign_space_byindex,
)
from topologist.helpers import string_to_coor_2d

run = ifcopenshell.api.run


class Molior:
    """A Builder, has resources to build"""

    def __init__(self, **args):
        self.file = None
        self.traces = {}
        self.hulls = {}
        self.normals = {}
        self.elevations = {}
        self.circulation = None
        self.cellcomplex = None
        self.share_dir = "share"
        self.Extrusion = Extrusion
        self.Floor = Floor
        self.Shell = Shell
        self.Space = Space
        self.Stair = Stair
        self.Wall = Wall
        self.Repeat = Repeat
        for arg in args:
            self.__dict__[arg] = args[arg]
        Molior.style = Style({"share_dir": self.share_dir})

    def execute(self):
        """Iterate through 'traces' and 'hulls' and populate an ifc 'file' object"""
        for condition in self.traces:
            for elevation in self.traces[condition]:
                level = self.elevations[elevation]
                for height in self.traces[condition][elevation]:
                    for stylename in self.traces[condition][elevation][height]:
                        for chain in self.traces[condition][elevation][height][
                            stylename
                        ]:
                            self.GetTraceIfc(
                                stylename,
                                condition,
                                level,
                                elevation,
                                height,
                                chain,
                            )
        for condition in self.hulls:
            for stylename in self.hulls[condition]:
                for hull in self.hulls[condition][stylename]:
                    self.GetHullIfc(
                        stylename,
                        condition,
                        hull,
                    )

        # use the topologic model to connect stuff
        if self.cellcomplex:
            for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
                if item.ContextIdentifier == "Reference":
                    reference_context = item

            structural_placement = self.file.createIfcLocalPlacement(
                None,
                self.file.createIfcAxis2Placement3D(
                    self.file.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                    self.file.createIfcDirection([0.0, 0.0, 1.0]),
                    self.file.createIfcDirection([1.0, 0.0, 0.0]),
                ),
            )

            # lookup tables to connect members to face indices
            surface_lookup = {}
            curve_list = []
            space_lookup = {}
            for member in self.file.by_type("IfcStructuralSurfaceMember"):
                member.ObjectPlacement = structural_placement
                pset_topology = ifcopenshell.util.element.get_psets(member).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    surface_lookup[pset_topology["FaceIndex"]] = member
            for member in self.file.by_type("IfcStructuralCurveMember"):
                member.ObjectPlacement = structural_placement
                pset_topology = ifcopenshell.util.element.get_psets(member).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    curve_list.append([pset_topology["FaceIndex"], member])
            for space in self.file.by_type("IfcSpace"):
                pset_topology = ifcopenshell.util.element.get_psets(space).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    space_lookup[pset_topology["CellIndex"]] = space

            # iterate all the edges in the topologic model
            edges_ptr = []
            self.cellcomplex.Edges(edges_ptr)
            point_list = []
            for edge in edges_ptr:
                v_start = edge.StartVertex()
                v_end = edge.EndVertex()
                start = list(v_start.Coordinates())
                end = list(v_end.Coordinates())

                # create an ifc curve connection for this topologic edge
                curve_connection = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcStructuralCurveConnection",
                    name="My Connection",
                )
                curve_connection.ObjectPlacement = structural_placement
                run(
                    "structural.assign_structural_analysis_model",
                    self.file,
                    product=curve_connection,
                    structural_analysis_model=self.file.by_type(
                        "IfcStructuralAnalysisModel"
                    )[0],
                )
                if abs(start[2] - end[2]) < 0.0001:
                    curve_connection.Axis = self.file.createIfcDirection(
                        [0.0, 0.0, 1.0]
                    )
                    curve_connection.Name = "Horizontal connection"
                elif (
                    abs(start[0] - end[0]) < 0.0001 and abs(start[1] - end[1]) < 0.0001
                ):
                    curve_connection.Axis = self.file.createIfcDirection(
                        [0.0, 1.0, 0.0]
                    )
                    curve_connection.Name = "Vertical connection"
                else:
                    vec_1 = subtract_3d(end, start)
                    vec_2 = [vec_1[1], 0.0 - vec_1[0], 0.0]
                    curve_connection.Axis = self.file.createIfcDirection(
                        x_product_3d(vec_1, vec_2)
                    )
                    curve_connection.Name = "Inclined connection"
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=curve_connection,
                    representation=self.file.createIfcTopologyRepresentation(
                        reference_context,
                        reference_context.ContextIdentifier,
                        "Edge",
                        [
                            self.file.createIfcEdge(
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(start)
                                ),
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(end)
                                ),
                            )
                        ],
                    ),
                )

                # loop though all the faces connected to this edge
                faces_ptr = []
                edge.Faces(faces_ptr)
                for face in faces_ptr:
                    index = face.Get("index")
                    # connect this surface member to this curve connection
                    if index and index in surface_lookup:
                        surface_member = surface_lookup[index]
                        run(
                            "structural.add_structural_member_connection",
                            self.file,
                            relating_structural_member=surface_member,
                            related_structural_connection=curve_connection,
                        )
                    # there is a curve member with this face index
                    for item in curve_list:
                        curve_index = item[0]
                        curve_member = item[1]
                        if not curve_index == index:
                            continue
                        # if index in curve_list:
                        if curve_connection.Name == "Horizontal connection":
                            connection_elevation = start[2]
                            curve_edge = curve_member.Representation.Representations[
                                0
                            ].Items[0]
                            # horizontal curve member coincides with this horizontal connection
                            if (
                                abs(
                                    curve_edge.EdgeStart.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                < 0.001
                                and abs(
                                    curve_edge.EdgeEnd.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                < 0.001
                            ):
                                run(
                                    "structural.add_structural_member_connection",
                                    self.file,
                                    relating_structural_member=curve_member,
                                    related_structural_connection=curve_connection,
                                )
                                # footings can have XYZ fixity, do it
                                is_footing = False
                                for referenced_by in curve_member.ReferencedBy:
                                    for related_object in referenced_by.RelatedObjects:
                                        if related_object.is_a("IfcFooting"):
                                            is_footing = True
                                if is_footing:
                                    run(
                                        "structural.add_structural_boundary_condition",
                                        self.file,
                                        name="foundation",
                                        connection=curve_connection,
                                    )
                                    run(
                                        "structural.edit_structural_boundary_condition",
                                        self.file,
                                        condition=curve_connection.AppliedCondition,
                                        attributes={
                                            "TranslationalStiffnessByLengthX": {
                                                "type": "IfcBoolean",
                                                "value": True,
                                            },
                                            "TranslationalStiffnessByLengthY": {
                                                "type": "IfcBoolean",
                                                "value": True,
                                            },
                                            "TranslationalStiffnessByLengthZ": {
                                                "type": "IfcBoolean",
                                                "value": True,
                                            },
                                            "RotationalStiffnessByLengthX": {
                                                "type": "IfcBoolean",
                                                "value": False,
                                            },
                                            "RotationalStiffnessByLengthY": {
                                                "type": "IfcBoolean",
                                                "value": False,
                                            },
                                            "RotationalStiffnessByLengthZ": {
                                                "type": "IfcBoolean",
                                                "value": False,
                                            },
                                        },
                                    )

                            # start point of non-horizontal curve member coincides with this horizontal connection
                            elif (
                                abs(
                                    curve_edge.EdgeStart.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                < 0.001
                                and abs(
                                    curve_edge.EdgeEnd.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                > 0.001
                            ):
                                connection_base = run(
                                    "root.create_entity",
                                    self.file,
                                    ifc_class="IfcStructuralPointConnection",
                                    name="Column base connection",
                                )
                                connection_base.ObjectPlacement = structural_placement
                                run(
                                    "geometry.assign_representation",
                                    self.file,
                                    product=connection_base,
                                    representation=self.file.createIfcTopologyRepresentation(
                                        reference_context,
                                        reference_context.ContextIdentifier,
                                        "Vertex",
                                        [
                                            self.file.createIfcVertexPoint(
                                                self.file.createIfcCartesianPoint(
                                                    curve_edge.EdgeStart.VertexGeometry.Coordinates
                                                )
                                            ),
                                        ],
                                    ),
                                )
                                run(
                                    "structural.assign_structural_analysis_model",
                                    self.file,
                                    product=connection_base,
                                    structural_analysis_model=self.file.by_type(
                                        "IfcStructuralAnalysisModel"
                                    )[0],
                                )
                                run(
                                    "structural.add_structural_member_connection",
                                    self.file,
                                    relating_structural_member=curve_member,
                                    related_structural_connection=connection_base,
                                )
                                point_list.append([connection_base, curve_connection])

                            # end point of non-horizontal curve member coincides with this horizontal connection
                            elif (
                                abs(
                                    curve_edge.EdgeStart.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                > 0.001
                                and abs(
                                    curve_edge.EdgeEnd.VertexGeometry.Coordinates[2]
                                    - connection_elevation
                                )
                                < 0.001
                            ):
                                connection_head = run(
                                    "root.create_entity",
                                    self.file,
                                    ifc_class="IfcStructuralPointConnection",
                                    name="Column head connection",
                                )
                                connection_head.ObjectPlacement = structural_placement
                                run(
                                    "geometry.assign_representation",
                                    self.file,
                                    product=connection_head,
                                    representation=self.file.createIfcTopologyRepresentation(
                                        reference_context,
                                        reference_context.ContextIdentifier,
                                        "Vertex",
                                        [
                                            self.file.createIfcVertexPoint(
                                                self.file.createIfcCartesianPoint(
                                                    curve_edge.EdgeEnd.VertexGeometry.Coordinates
                                                )
                                            ),
                                        ],
                                    ),
                                )
                                run(
                                    "structural.assign_structural_analysis_model",
                                    self.file,
                                    product=connection_head,
                                    structural_analysis_model=self.file.by_type(
                                        "IfcStructuralAnalysisModel"
                                    )[0],
                                )
                                run(
                                    "structural.add_structural_member_connection",
                                    self.file,
                                    relating_structural_member=curve_member,
                                    related_structural_connection=connection_head,
                                )
                                point_list.append([connection_head, curve_connection])

            # attach column point connections to beams/footings/slabs/walls
            for item in point_list:
                connection_point = item[0]
                connection_curve = item[1]
                for rel in connection_curve.ConnectsStructuralMembers:
                    member = rel.RelatingStructuralMember
                    run(
                        "structural.add_structural_member_connection",
                        self.file,
                        relating_structural_member=member,
                        related_structural_connection=connection_point,
                    )

            # delete unused curve connections
            for curve_connection in self.file.by_type("IfcStructuralCurveConnection"):
                if len(curve_connection.ConnectsStructuralMembers) < 2:
                    for relation in curve_connection.ConnectsStructuralMembers:
                        run(
                            "structural.remove_structural_connection_condition",
                            self.file,
                            relation=relation,
                        )
                    run("root.remove_product", self.file, product=curve_connection)

            # attach spaces to space boundaries
            for boundary in self.file.by_type("IfcRelSpaceBoundary2ndLevel"):
                if boundary.Description:
                    items = boundary.Description.split()
                    if len(items) == 2 and items[0] == "CellIndex":
                        if items[1] in space_lookup:
                            boundary.RelatingSpace = space_lookup[items[1]]

            # attach Slab elements to relevant Space
            for element in self.file.by_type("IfcSlab"):
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    assign_space_byindex(self.file, element, pset_topology["CellIndex"])

            # attach Window elements to relevant Space
            for element in self.file.by_type("IfcWindow"):
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    assign_space_byindex(
                        self.file, element, pset_topology["BackCellIndex"]
                    )

            # attach Door elements to Space
            cells_ptr = []
            self.cellcomplex.Cells(cells_ptr)
            cells = {}
            for cell in cells_ptr:
                cells[cell.Get("index")] = cell

            for element in self.file.by_type("IfcDoor"):
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    if not "FrontCellIndex" in pset_topology or (
                        "FrontCellIndex" in pset_topology
                        and cells[pset_topology["FrontCellIndex"]].IsOutside()
                    ):
                        assign_space_byindex(
                            self.file, element, pset_topology["BackCellIndex"]
                        )
                    elif cells[pset_topology["BackCellIndex"]].IsOutside():
                        assign_space_byindex(
                            self.file, element, pset_topology["FrontCellIndex"]
                        )
                    else:
                        if cells[pset_topology["FrontCellIndex"]].Get(
                            "separation"
                        ) and float(
                            cells[pset_topology["FrontCellIndex"]].Get("separation")
                        ) > float(
                            cells[pset_topology["BackCellIndex"]].Get("separation")
                        ):
                            assign_space_byindex(
                                self.file, element, pset_topology["FrontCellIndex"]
                            )
                        else:
                            assign_space_byindex(
                                self.file, element, pset_topology["BackCellIndex"]
                            )

    def GetTraceIfc(
        self,
        stylename,
        condition,
        level,
        elevation,
        height,
        chain,
    ):
        """Retrieves IFC data and adds to model"""
        results = []
        myconfig = Molior.style.get(stylename)
        for name in myconfig["traces"]:
            config = myconfig["traces"][name]
            if "condition" in config and config["condition"] == condition:
                closed = 0
                if chain.is_simple_cycle():
                    closed = 1
                path = []
                for node in chain.nodes():
                    path.append(string_to_coor_2d(node))
                normal_set = "bottom"
                if re.search("^top-", condition):
                    normal_set = "top"
                vals = {
                    "closed": closed,
                    "path": path,
                    "cellcomplex": self.cellcomplex,
                    "chain": chain,
                    "circulation": self.circulation,
                    "file": self.file,
                    "name": name,
                    "elevation": elevation,
                    "height": height,
                    "normals": self.normals,
                    "normal_set": normal_set,
                    "style": stylename,
                    "level": level,
                    "style_openings": myconfig["openings"],
                    "style_assets": myconfig["assets"],
                    "style_materials": myconfig["materials"],
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results

    def GetHullIfc(self, stylename, condition, hull):
        """Retrieves IFC data and adds to model"""
        results = []
        myconfig = Molior.style.get(stylename)
        for name in myconfig["hulls"]:
            config = myconfig["hulls"][name]
            if "condition" in config and config["condition"] == condition:
                vals = {
                    "cellcomplex": self.cellcomplex,
                    "file": self.file,
                    "name": name,
                    "style": stylename,
                    "hull": hull,
                    "style_materials": myconfig["materials"],
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results
