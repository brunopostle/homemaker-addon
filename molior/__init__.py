"""Molior builds 3D models from topologist 'traces' and 'hulls'

Which traces and hulls are used, and how they are used, are defined by files in
the 'share' folder and subfolders.  Access to these style
definitions is handled by the .style module.

Molior uses IfcOpenShell to generate IFC models of buildings, with
some extra helper methods defined in the .ifc module.  Different
building parts need to be constructed differently, so walls, floors,
extrusions etc. are each handled by dedicated modules.

Molior is largely derived from the Perl 'Molior' module, but has been
rewritten in python in order to interface with Topologic and
IfcOpenShell.

"""

import re
import ifcopenshell.util
from topologic import CellComplex, CellUtility, Vertex, Face, Topology
from .extrusion import Extrusion
from .floor import Floor
from .shell import Shell
from .space import Space
from .stair import Stair
from .wall import Wall
from .repeat import Repeat
from .grillage import Grillage

from .style import Style
from .geometry import subtract_3d, x_product_3d, matrix_align
from .ifc import (
    init,
    get_site_by_name,
    get_building_by_name,
    get_structural_analysis_model_by_name,
    create_default_contexts,
    create_storeys,
    add_cell_topology_epsets,
    assign_space_byindex,
    assign_storey_byindex,
    get_context_by_name,
    get_parent_building,
    create_tessellation_from_mesh,
    create_tessellations_from_mesh_split,
)
import topologist.ushell as ushell
import topologist.ugraph as ugraph
from topologist.helpers import string_to_coor

api = ifcopenshell.api


class Molior:
    """A Builder, has resources to build"""

    @classmethod
    def from_faces_and_widgets(
        cls, file=None, faces=[], widgets=[], name="My Building", share_dir="share"
    ):
        """Create a Molior object from lists of Topologic Faces and widgets."""
        """Faces can have a 'style' Dictionary attribute."""
        """Widgets are Topologic Vertices with a 'usage' Dictionary attribute."""
        # Generate a Topologic CellComplex
        cellcomplex = CellComplex.ByFaces(faces, 0.0001)

        result = []
        cellcomplex.Faces(None, result)
        if result:
            # Copy styles from Faces to the CellComplex
            cellcomplex.ApplyDictionary(faces)
            # Assign Cell usages from widgets
            cellcomplex.AllocateCells(widgets)
            return cls.from_cellcomplex(
                file=file, cellcomplex=cellcomplex, name=name, share_dir=share_dir
            )

        topology = Topology.ByFaces(faces, 0.0001)

        result = []
        topology.Faces(None, result)
        if result:
            # Copy styles from Faces to the Topology
            topology.ApplyDictionary(faces)
            return cls.from_topology(
                file=file, topology=topology, name=name, share_dir=share_dir
            )

    @classmethod
    def from_cellcomplex(
        cls, file=None, cellcomplex=None, name="My Building", share_dir="share"
    ):
        """Create a Molior object from a tagged CellComplex"""
        """Faces in the CellComplex can have a 'style' Dictionary attribute."""
        """Cells in the CellComplex can have a 'usage' Dictionary attribute."""
        # Give every Cell and Face an index number
        cellcomplex.IndexTopology()
        # Generate a circulation Graph
        circulation = cellcomplex.Adjacency()
        circulation.Circulation(cellcomplex)
        circulation.Separation(circulation.ShortestPathTable(), cellcomplex)

        # Traces are 2D paths that define walls, extrusions and rooms
        # Hulls are 3D shells that define pitched roofs and soffits
        # Collect unique elevations and assign storey numbers
        traces, normals, elevations = cellcomplex.GetTraces()
        hulls = cellcomplex.GetHulls()

        return cls(
            file=file,
            circulation=circulation,
            traces=traces,
            elevations=elevations,
            name=name,
            hulls=hulls,
            normals=normals,
            cellcomplex=cellcomplex,
            share_dir=share_dir,
        )

    @classmethod
    def from_topology(
        cls, file=None, topology=None, name="My Building", share_dir="share"
    ):
        """Create a Molior object from a tagged Topology"""
        """Faces in the CellComplex can have a 'style' Dictionary attribute."""
        # Give every Cell and Face an index number
        topology.IndexTopology()
        traces, normals, elevations = topology.GetTraces()
        hulls = topology.GetHulls()

        return cls(
            file=file,
            traces=traces,
            elevations=elevations,
            name=name,
            hulls=hulls,
            normals=normals,
            share_dir=share_dir,
        )

    @classmethod
    def get_cellcomplex_from_ifc(cls, entity):
        """Retrieve a CellComplex definition stored by the stash_topology() method"""
        """Supply an IfcBuilding or any element or space within that building"""
        """A Topologic CellComplex or None will be returned"""
        building = get_parent_building(entity)
        if not building:
            return None

        faces_ptr = []
        widgets = []
        for representation in building.Representation.Representations:
            context = representation.ContextOfItems
            if (
                context.is_a("IfcGeometricRepresentationSubContext")
                and context.ContextIdentifier == "Reference"
                and context.ContextType == "Model"
                and context.TargetView == "SKETCH_VIEW"
            ):
                for item in representation.Items:
                    if item.is_a("IfcPolygonalFaceSet"):
                        stylename = item.StyledByItem[0].Name
                        coordinates = item.Coordinates.CoordList
                        vertices = [Vertex.ByCoordinates(*v) for v in coordinates]
                        for face in item.Faces:
                            indices = face.CoordIndex
                            face_ptr = Face.ByVertices(
                                [vertices[v - 1] for v in indices]
                            )
                            face_ptr.Set(
                                "stylename",
                                stylename,
                            )
                            faces_ptr.append(face_ptr)

        for rel in building.ContainsElements:
            for element in rel.RelatedElements:
                if element.is_a("IfcAnnotation") and element.ObjectType == "USAGE":
                    matrix = ifcopenshell.util.placement.get_local_placement(
                        element.ObjectPlacement
                    )
                    vertex = Vertex.ByCoordinates(
                        matrix[0][3], matrix[1][3], matrix[2][3]
                    )
                    vertex.Set(
                        "usage",
                        element.Name,
                    )
                    widgets.append(vertex)

        if not faces_ptr:
            return None

        cellcomplex = CellComplex.ByFaces(faces_ptr, 0.0001)
        cellcomplex.ApplyDictionary(faces_ptr)
        cellcomplex.AllocateCells(widgets)
        cellcomplex.Set("name", building.Name)
        return cellcomplex

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
        if self.file is None:
            self.file = init()
        else:
            create_default_contexts(self.file)
        self.project = self.file.by_type("IfcProject")[0]
        site = get_site_by_name(self.file, self.project, self.name)
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
            self.file, context_identifier="Reference", target_view="GRAPH_VIEW"
        )

        structural_placement = self.file.createIfcLocalPlacement(
            None,
            self.file.createIfcAxis2Placement3D(
                self.file.createIfcCartesianPoint([0.0, 0.0, 0.0]),
                self.file.createIfcDirection([0.0, 0.0, 1.0]),
                self.file.createIfcDirection([1.0, 0.0, 0.0]),
            ),
        )

        style = api.style.add_style(self.file, name="Structural Surface Member")
        api.style.add_surface_style(
            self.file,
            style=style,
            ifc_class="IfcSurfaceStyleShading",
            attributes={
                "SurfaceColour": {
                    "Name": None,
                    "Red": 0.5,
                    "Green": 0.5,
                    "Blue": 0.0,
                },
                "Transparency": 0.95,
            },
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
            self.file.createIfcStyledItem(
                member.Representation.Representations[0].Items[0],
                [style],
                "Structural Surface Member",
            )
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
            curve_connection = api.root.create_entity(
                self.file,
                ifc_class="IfcStructuralCurveConnection",
                name="My Connection",
            )
            curve_connection.ObjectPlacement = structural_placement
            api.structural.assign_structural_analysis_model(
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
            api.geometry.assign_representation(
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
                if index is not None and index in surface_lookup:
                    surface_member = surface_lookup[index]
                    api.structural.add_structural_member_connection(
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
                            api.structural.add_structural_member_connection(
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
                                api.structural.add_structural_boundary_condition(
                                    self.file,
                                    name="foundation",
                                    connection=curve_connection,
                                )
                                api.structural.edit_structural_boundary_condition(
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

                            point_connection = api.root.create_entity(
                                self.file,
                                ifc_class="IfcStructuralPointConnection",
                                name=point_connection_name,
                            )
                            point_connection.ObjectPlacement = structural_placement
                            api.geometry.assign_representation(
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
                            api.structural.assign_structural_analysis_model(
                                self.file,
                                product=point_connection,
                                structural_analysis_model=self.structural_analysis_model,
                            )
                            api.structural.add_structural_member_connection(
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
                api.structural.add_structural_member_connection(
                    self.file,
                    relating_structural_member=member,
                    related_structural_connection=connection_point,
                )

        # delete unused curve connections
        for curve_connection in self.file.by_type("IfcStructuralCurveConnection"):
            if len(curve_connection.ConnectsStructuralMembers) < 2:
                for relation in curve_connection.ConnectsStructuralMembers:
                    api.structural.remove_structural_connection_condition(
                        self.file,
                        relation=relation,
                    )
                api.root.remove_product(self.file, product=curve_connection)

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
            if topology_index is not None and topology_index in space_lookup:
                continue
            else:
                element = api.root.create_entity(
                    self.file,
                    ifc_class="IfcSpace",
                    name="void-space/" + str(topology_index),
                )
                if topology_index is not None:
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
                style = api.style.add_style(self.file, name="Void Space")
                api.style.add_surface_style(
                    self.file,
                    style=style,
                    ifc_class="IfcSurfaceStyleShading",
                    attributes={
                        "SurfaceColour": {
                            "Name": None,
                            "Red": 0.5,
                            "Green": 0.5,
                            "Blue": 0.5,
                        },
                        "Transparency": 0.5,
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

        # .floor attaches elements directly to Storey, re-attach to relevant Space
        for element in self.file.by_type("IfcBuildingElement"):
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
                    if "FrontCellIndex" not in pset_topology or (
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
        # Cellcomplex stashed as Tessellation representation items
        sketch_context = get_context_by_name(
            self.file,
            parent_context_identifier="Model",
            context_identifier="Reference",
            target_view="SKETCH_VIEW",
        )
        api.geometry.assign_representation(
            self.file,
            product=self.building,
            representation=self.file.createIfcShapeRepresentation(
                sketch_context,
                sketch_context.ContextIdentifier,
                "Tessellation",
                create_tessellations_from_mesh_split(
                    self.file, *self.cellcomplex.MeshSplit()
                ),
            ),
        )
        # A FootPrint representation will have visualisation priority
        footprint_context = get_context_by_name(
            self.file,
            parent_context_identifier="Model",
            context_identifier="FootPrint",
            target_view="PLAN_VIEW",
        )
        paths = self.cellcomplex.FootPrint()
        if paths:
            polycurves = []
            for path in paths:
                vertices = [string_to_coor(vertex) for vertex in path.graph]
                if path.is_simple_cycle():
                    vertices.append(vertices[0])
                point_list = self.file.createIfcCartesianPointList3D(vertices)
                polycurves.append(
                    self.file.createIfcIndexedPolyCurve(point_list, None, False)
                )
            api.geometry.assign_representation(
                self.file,
                product=self.building,
                representation=self.file.createIfcShapeRepresentation(
                    footprint_context,
                    footprint_context.ContextIdentifier,
                    "Curve3D",
                    polycurves,
                ),
            )

        # Create a Virtual Element with a Point Representation for each Cell
        cells = []
        self.cellcomplex.Cells(None, cells)
        for cell in cells:
            vertex = CellUtility.InternalVertex(cell, 0.001)

            # stash the space usage as an annotation
            annotation = api.root.create_entity(
                self.file,
                ifc_class="IfcAnnotation",
                predefined_type="USAGE",
                name=cell.Get("usage"),
            )
            api.geometry.edit_object_placement(
                self.file,
                product=annotation,
                matrix=matrix_align(vertex.Coordinates(), [1.0, 0.0, 0.0]),
            )
            api.spatial.assign_container(
                self.file,
                products=[annotation],
                relating_structure=self.building,
            )

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
                closed = False
                if chain.is_simple_cycle():
                    closed = True
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
                    "style_families": myconfig["families"],
                    "style_object": Molior.style,
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
                    "normals": {},
                    "normal_set": "bottom",
                    "style": stylename,
                    "hull": hull,
                    "style_families": myconfig["families"],
                    "style_object": Molior.style,
                }
                vals.update(config)
                modules = {"Shell": Shell, "Grillage": Grillage}
                part = modules[config["class"]](vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results
