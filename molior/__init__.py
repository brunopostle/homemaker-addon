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
from topologic import CellUtility
from molior.extrusion import Extrusion
from molior.floor import Floor
from molior.shell import Shell
from molior.space import Space
from molior.stair import Stair
from molior.wall import Wall
from molior.repeat import Repeat
from molior.grillage import Grillage

from molior.style import Style
from molior.geometry import subtract_3d, x_product_3d, matrix_align
import molior.ifc
from molior.ifc import (
    get_site_by_name,
    get_building_by_name,
    get_structural_analysis_model_by_name,
    create_storeys,
    add_cell_topology_epsets,
    add_topologic_epsets,
    assign_space_byindex,
    assign_storey_byindex,
    get_context_by_name,
    get_parent_building,
    create_tessellation_from_mesh,
)
import topologist.ushell as ushell
import topologist.ugraph as ugraph

run = ifcopenshell.api.run


class Molior:
    """A Builder, has resources to build"""

    def __init__(self, **args):
        self.file = None
        self.building = None
        self.structural_analysis_model = None
        self.traces = {}
        self.hulls = {}
        self.normals = {}
        self.elevations = {}
        self.name = "Homemaker Building"
        self.circulation = None
        self.cellcomplex = None
        self.share_dir = "share"
        for arg in args:
            self.__dict__[arg] = args[arg]
        Molior.style = Style({"share_dir": self.share_dir})

    def init_building(self):
        """Create and relate Site, Building and Storey Spatial Element products, set as current building"""
        if self.file == None:
            self.file = molior.ifc.init()
        self.project = self.file.by_type("IfcProject")[0]
        site = get_site_by_name(self.file, self.project, "Site " + self.name)
        self.building = get_building_by_name(self.file, site, self.name)
        self.structural_analysis_model = get_structural_analysis_model_by_name(
            self.file, self.building, self.name
        )
        create_storeys(self.file, self.building, self.elevations)

    def execute(self):
        """Iterate through 'traces' and 'hulls' and populate an ifc 'file' object"""
        self.init_building()
        for condition in self.traces:
            for elevation in self.traces[condition]:
                for height in self.traces[condition][elevation]:
                    for stylename in self.traces[condition][elevation][height]:
                        for chain in self.traces[condition][elevation][height][
                            stylename
                        ]:
                            self.build_trace(
                                stylename=stylename,
                                condition=condition,
                                elevation=elevation,
                                height=height,
                                chain=chain,
                            )
        for condition in self.hulls:
            for stylename in self.hulls[condition]:
                for hull in self.hulls[condition][stylename]:
                    self.build_hull(
                        stylename=stylename,
                        condition=condition,
                        hull=hull,
                    )

        # use the topologic model to connect stuff
        if self.cellcomplex:
            self.connect_structure()
            self.connect_spaces()
            self.stash_topology()

    def connect_structure(self):
        """Given Structural Member entities are tagged with Topologic indexes, connect them"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )

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
        for member in self.file.by_type("IfcStructuralSurfaceMember"):
            if get_parent_building(member) == self.building:
                member.ObjectPlacement = structural_placement
                pset_topology = ifcopenshell.util.element.get_psets(member).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    surface_lookup[pset_topology["FaceIndex"]] = member
        for member in self.file.by_type("IfcStructuralCurveMember"):
            if get_parent_building(member) == self.building:
                member.ObjectPlacement = structural_placement
                pset_topology = ifcopenshell.util.element.get_psets(member).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    curve_list.append([pset_topology["FaceIndex"], member])

        # iterate all the edges in the topologic model
        edges_ptr = []
        self.cellcomplex.Edges(None, edges_ptr)
        point_list = []
        for edge in edges_ptr:
            v_start = edge.StartVertex()
            v_end = edge.EndVertex()
            start = v_start.Coordinates()
            end = v_end.Coordinates()

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
                structural_analysis_model=self.structural_analysis_model,
            )
            if abs(start[2] - end[2]) < 0.0001:
                curve_connection.Axis = self.file.createIfcDirection([0.0, 0.0, 1.0])
                curve_connection.Name = "Horizontal connection"
            elif abs(start[0] - end[0]) < 0.0001 and abs(start[1] - end[1]) < 0.0001:
                curve_connection.Axis = self.file.createIfcDirection([0.0, 1.0, 0.0])
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
            # TODO merge duplicate columns

            # loop though all the faces connected to this edge
            faces_ptr = edge.Faces_Cached(self.cellcomplex)
            for face in faces_ptr:
                index = face.Get("index")
                # connect this surface member to this curve connection
                if not index == None and index in surface_lookup:
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
                        start_coors = curve_edge.EdgeStart.VertexGeometry.Coordinates
                        end_coors = curve_edge.EdgeEnd.VertexGeometry.Coordinates

                        # member is horizontal and coincides with this horizontal connection
                        if (
                            abs(start_coors[2] - connection_elevation) < 0.001
                            and abs(end_coors[2] - connection_elevation) < 0.001
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

                        # FIXME connect ends of horizontal members to other members
                        # member is non-horizontal, but one end coincides with this horizontal connection
                        elif (
                            abs(start_coors[2] - connection_elevation) < 0.001
                            or abs(end_coors[2] - connection_elevation) < 0.001
                        ):

                            # start point of non-horizontal curve member coincides with this horizontal connection
                            if abs(start_coors[2] - connection_elevation) < 0.001:
                                point_connection_name = "Column base connection"
                                point_coordinates = start_coors

                            # end point of non-horizontal curve member coincides with this horizontal connection
                            elif abs(start_coors[2] - connection_elevation) > 0.001:
                                point_connection_name = "Column head connection"
                                point_coordinates = end_coors

                            point_connection = run(
                                "root.create_entity",
                                self.file,
                                ifc_class="IfcStructuralPointConnection",
                                name=point_connection_name,
                            )
                            point_connection.ObjectPlacement = structural_placement
                            run(
                                "geometry.assign_representation",
                                self.file,
                                product=point_connection,
                                representation=self.file.createIfcTopologyRepresentation(
                                    reference_context,
                                    reference_context.ContextIdentifier,
                                    "Vertex",
                                    [
                                        self.file.createIfcVertexPoint(
                                            self.file.createIfcCartesianPoint(
                                                point_coordinates
                                            )
                                        ),
                                    ],
                                ),
                            )
                            run(
                                "structural.assign_structural_analysis_model",
                                self.file,
                                product=point_connection,
                                structural_analysis_model=self.structural_analysis_model,
                            )
                            run(
                                "structural.add_structural_member_connection",
                                self.file,
                                relating_structural_member=curve_member,
                                related_structural_connection=point_connection,
                            )
                            point_list.append([point_connection, curve_connection])

        # TODO merge coincident Point Connections
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

    def connect_spaces(self):
        """Given objects and boundaries are tagged with Topologic indexes, assign them to correct spaces"""
        body_context = get_context_by_name(self.file, context_identifier="Body")

        space_lookup = {}
        for space in self.file.by_type("IfcSpace"):
            if get_parent_building(space) == self.building:
                pset_topology = ifcopenshell.util.element.get_psets(space).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    space_lookup[pset_topology["CellIndex"]] = space

        # create Space elements for Cells that don't already have one
        cells_ptr = []
        self.cellcomplex.Cells(None, cells_ptr)
        for cell in cells_ptr:
            topology_index = cell.Get("index")
            if not topology_index == None and topology_index in space_lookup:
                continue
            else:
                element = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcSpace",
                    name="void-space/" + str(topology_index),
                )
                if not topology_index == None:
                    space_lookup[topology_index] = element
                    add_cell_topology_epsets(self.file, element, cell)
                elevation = cell.Elevation()
                level = 0
                if elevation in self.elevations:
                    level = self.elevations[elevation]
                storey = assign_storey_byindex(self.file, element, self.building, level)
                vertices, faces = cell.Mesh()
                # not sure why this is necessary
                vertices_shifted = [
                    [v[0], v[1], v[2] - storey.Elevation] for v in vertices
                ]
                shape = self.file.createIfcShapeRepresentation(
                    body_context,
                    body_context.ContextIdentifier,
                    "Tessellation",
                    [create_tessellation_from_mesh(self.file, vertices_shifted, faces)],
                )
                style = run("style.add_style", self.file, name="Void Space")
                run(
                    "style.add_surface_style",
                    self.file,
                    style=style,
                    attributes={
                        "SurfaceColour": {
                            "Name": None,
                            "Red": 0.5,
                            "Green": 0.5,
                            "Blue": 0.5,
                        },
                        "DiffuseColour": {
                            "Name": None,
                            "Red": 0.5,
                            "Green": 0.5,
                            "Blue": 0.5,
                        },
                        "Transparency": 0.5,
                        "ReflectanceMethod": "PLASTIC",
                    },
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
                    product=element,
                    representation=shape,
                )
                run(
                    "geometry.edit_object_placement",
                    self.file,
                    product=element,
                    matrix=matrix_align([0.0, 0.0, storey.Elevation], [1.0, 0.0, 0.0]),
                )

        # attach spaces to space boundaries
        for boundary in self.file.by_type("IfcRelSpaceBoundary2ndLevel"):
            if get_parent_building(boundary.RelatedBuildingElement) == self.building:
                if boundary.Description:
                    items = boundary.Description.split()
                    if len(items) == 2 and items[0] == "CellIndex":
                        if items[1] in space_lookup:
                            boundary.RelatingSpace = space_lookup[items[1]]
                            # there ought to be a better way..
                            storey_elevation = boundary.RelatingSpace.Decomposes[
                                0
                            ].RelatingObject.Elevation
                            coor = (
                                boundary.ConnectionGeometry.SurfaceOnRelatingElement.BasisSurface.Position.Location.Coordinates
                            )
                            boundary.ConnectionGeometry.SurfaceOnRelatingElement.BasisSurface.Position.Location.Coordinates = (
                                coor[0],
                                coor[1],
                                coor[2] - storey_elevation,
                            )
                for (
                    element_boundary
                ) in boundary.RelatedBuildingElement.ProvidesBoundaries:
                    if (
                        element_boundary.Name
                        and element_boundary.Name == boundary.Name
                        and element_boundary != boundary
                    ):
                        boundary.CorrespondingBoundary = element_boundary

        # molior.floor attaches Slab elements directly to Storey, re-attach to relevant Space
        for element in self.file.by_type("IfcSlab"):
            if get_parent_building(element) == self.building:
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology and "CellIndex" in pset_topology:
                    assign_space_byindex(
                        self.file, element, self.building, pset_topology["CellIndex"]
                    )

        # attach Window elements to relevant Space
        for element in self.file.by_type("IfcWindow"):
            if get_parent_building(element) == self.building:
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    assign_space_byindex(
                        self.file,
                        element,
                        self.building,
                        pset_topology["BackCellIndex"],
                    )

        cell_lookup = {}
        cells_ptr = []
        self.cellcomplex.Cells(None, cells_ptr)
        for cell in cells_ptr:
            cell_lookup[cell.Get("index")] = cell

        # attach Door elements to Space
        for element in self.file.by_type("IfcDoor"):
            if get_parent_building(element) == self.building:
                pset_topology = ifcopenshell.util.element.get_psets(element).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    if not "FrontCellIndex" in pset_topology or (
                        "FrontCellIndex" in pset_topology
                        and cell_lookup[pset_topology["FrontCellIndex"]].IsOutside()
                    ):
                        assign_space_byindex(
                            self.file,
                            element,
                            self.building,
                            pset_topology["BackCellIndex"],
                        )
                    elif cell_lookup[pset_topology["BackCellIndex"]].IsOutside():
                        assign_space_byindex(
                            self.file,
                            element,
                            self.building,
                            pset_topology["FrontCellIndex"],
                        )
                    else:
                        if cell_lookup[pset_topology["FrontCellIndex"]].Get(
                            "separation"
                        ) and float(
                            cell_lookup[pset_topology["FrontCellIndex"]].Get(
                                "separation"
                            )
                        ) > float(
                            cell_lookup[pset_topology["BackCellIndex"]].Get(
                                "separation"
                            )
                        ):
                            assign_space_byindex(
                                self.file,
                                element,
                                self.building,
                                pset_topology["FrontCellIndex"],
                            )
                        else:
                            assign_space_byindex(
                                self.file,
                                element,
                                self.building,
                                pset_topology["BackCellIndex"],
                            )

    def stash_topology(self):
        """Represent a Topologic model as IFC geometry"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        system = run("system.add_system", self.file)
        system.Name = "Topology/" + self.building.Name
        rel = run(
            "root.create_entity",
            self.file,
            ifc_class="IfcRelServicesBuildings",
            name=system.Name,
        )
        rel.RelatingSystem = system
        rel.RelatedBuildings = [self.building]

        style = run("style.add_style", self.file, name="CellComplex")
        run(
            "style.add_surface_style",
            self.file,
            style=style,
            attributes={
                "SurfaceColour": {
                    "Name": "Translucent Blue",
                    "Red": 0.2,
                    "Green": 0.2,
                    "Blue": 1.0,
                },
                "Transparency": 0.8,
                "ReflectanceMethod": "PLASTIC",
            },
        )

        # Create a Virtual Element with a Shape Representation for each Face
        faces = []
        self.cellcomplex.Faces(None, faces)
        for face in faces:
            element = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcVirtualElement",
                name="face/" + str(face.Get("index")),
            )
            run("system.assign_system", self.file, product=element, system=system)
            run(
                "spatial.assign_container",
                self.file,
                product=element,
                relating_structure=self.building,
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=element,
                representation=self.file.createIfcShapeRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Tessellation",
                    [create_tessellation_from_mesh(self.file, *face.Mesh())],
                ),
            )
            run(
                "style.assign_representation_styles",
                self.file,
                shape_representation=element.Representation.Representations[0],
                styles=[style],
            )
            add_topologic_epsets(self.file, element, face)

        # Create a Virtual Element with a Point Representation for each Cell
        cells = []
        self.cellcomplex.Cells(None, cells)
        for cell in cells:
            element = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcVirtualElement",
                name="cell/" + str(cell.Get("index")),
            )
            run("system.assign_system", self.file, product=element, system=system)
            run(
                "spatial.assign_container",
                self.file,
                product=element,
                relating_structure=self.building,
            )
            vertex = CellUtility.InternalVertex(cell, 0.001)
            point = self.file.createIfcCartesianPoint(vertex.Coordinates())
            run(
                "geometry.assign_representation",
                self.file,
                product=element,
                representation=self.file.createIfcShapeRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "PointCloud",  # should be Point
                    [point],
                ),
            )
            add_topologic_epsets(self.file, element, cell)

    def build_trace(
        self,
        stylename="default",
        condition="external",
        elevation=0.0,
        height=2.7,
        chain=ugraph.graph(),
    ):
        """Generates IFC data for a single trace and adds to the current building"""
        results = []
        myconfig = Molior.style.get(stylename)
        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        for name in myconfig["traces"]:
            config = myconfig["traces"][name]
            if "condition" in config and config["condition"] == condition:
                closed = 0
                if chain.is_simple_cycle():
                    closed = 1
                path = []
                for node in chain.graph:
                    path.append(chain.graph[node][1]["start_vertex"].Coordinates()[0:2])
                if not closed:
                    last_node = list(chain.graph)[-1]
                    path.append(
                        chain.graph[last_node][1]["end_vertex"].Coordinates()[0:2]
                    )
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
                    "building": self.building,
                    "structural_analysis_model": self.structural_analysis_model,
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
                modules = {
                    "Extrusion": Extrusion,
                    "Floor": Floor,
                    "Space": Space,
                    "Stair": Stair,
                    "Wall": Wall,
                    "Repeat": Repeat,
                }
                part = modules[config["class"]](vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results

    def build_hull(self, stylename="default", condition="panel", hull=ushell.shell()):
        """Generates IFC data for a single hull and adds to the current building"""
        results = []
        myconfig = Molior.style.get(stylename)
        for name in myconfig["hulls"]:
            config = myconfig["hulls"][name]
            if "condition" in config and config["condition"] == condition:
                vals = {
                    "cellcomplex": self.cellcomplex,
                    "elevations": self.elevations,
                    "file": self.file,
                    "building": self.building,
                    "structural_analysis_model": self.structural_analysis_model,
                    "name": name,
                    "style": stylename,
                    "hull": hull,
                    "style_materials": myconfig["materials"],
                }
                vals.update(config)
                modules = {"Shell": Shell, "Grillage": Grillage}
                part = modules[config["class"]](vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results
