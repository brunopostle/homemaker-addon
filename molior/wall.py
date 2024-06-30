import ifcopenshell.api.type
import ifcopenshell.api.void
import ifcopenshell.geom
import numpy

from topologic import Vertex, Edge, Face, FaceUtility
from topologist.helpers import el
from molior.baseclass import TraceClass
from molior.geometry import (
    matrix_align,
    add_2d,
    scale_2d,
    distance_2d,
    subtract_3d,
    add_3d,
    transform,
    map_to_2d_simple,
)
from molior.ifc import (
    add_face_topology_epsets,
    create_extruded_area_solid,
    clip_solid,
    create_face_surface,
    assign_storey_byindex,
    get_type_object,
    get_material_by_name,
    get_context_by_name,
    get_thickness,
    create_curve_bounded_plane,
    create_closed_profile_from_points,
)

api = ifcopenshell.api


class Wall(TraceClass):
    """A vertical wall, internal or external"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ceiling = 0.35
        self.ifc = "IfcWall"
        self.party_wall = False
        self.structural_material = "Masonry"
        self.structural_thickness = 0.2
        self.openings = []
        self.path = []
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""

        #  contexts

        reference_context = get_context_by_name(
            self.file, context_identifier="Reference", target_view="GRAPH_VIEW"
        )
        body_context = get_context_by_name(self.file, context_identifier="Body")
        axis_context = get_context_by_name(self.file, context_identifier="Axis")
        clearance_context = get_context_by_name(
            self.file, context_identifier="Clearance"
        )

        self.init_openings()

        # traces have one or more segments, aggregate them
        aggregate = api.root.create_entity(
            self.file,
            ifc_class="IfcElementAssembly",
            name=self.name,
        )
        api.geometry.edit_object_placement(
            self.file,
            product=aggregate,
            matrix=matrix_align(
                [*self.corner_coor(0), self.elevation],
                [*self.corner_coor(1), self.elevation],
            ),
        )
        assign_storey_byindex(self.file, aggregate, self.building, self.level)

        previous_wall = None
        segments = self.segments()
        for id_segment in range(segments):
            mywall = api.root.create_entity(
                self.file,
                ifc_class=self.ifc,
                name=self.name,
            )

            api.aggregate.assign_object(
                self.file,
                products=[mywall],
                relating_object=aggregate,
            )

            segment = self.chain.edges()[id_segment]
            face = self.chain.graph[segment[0]][1]["face"]
            vertices_ptr = []
            self.chain.graph[segment[0]][1]["face"].VerticesPerimeter(vertices_ptr)
            vertices = [vertex.Coordinates() for vertex in vertices_ptr]
            normal = self.chain.graph[segment[0]][1]["face"].Normal()

            # generate space boundaries
            boundaries = []
            cells_ordered = face.CellsOrdered(self.cellcomplex)
            for cell in cells_ordered:
                if cell is None:
                    boundaries.append(None)
                    continue
                boundary = api.root.create_entity(
                    self.file,
                    ifc_class="IfcRelSpaceBoundary2ndLevel",
                )
                if self.party_wall:
                    boundary.InternalOrExternalBoundary = "EXTERNAL_FIRE"
                elif face.IsInternal(self.cellcomplex):
                    boundary.InternalOrExternalBoundary = "INTERNAL"
                else:
                    boundary.InternalOrExternalBoundary = "EXTERNAL"
                if mywall.is_a("IfcVirtualElement"):
                    boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                else:
                    boundary.PhysicalOrVirtualBoundary = "PHYSICAL"

                boundary.RelatedBuildingElement = mywall
                if cell == cells_ordered[0]:
                    # the face points to this cell
                    nodes_2d, matrix = map_to_2d_simple(
                        reversed(vertices), [-v for v in normal]
                    )
                else:
                    nodes_2d, matrix = map_to_2d_simple(vertices, normal)

                curve_bounded_plane = create_curve_bounded_plane(
                    self.file, nodes_2d, matrix
                )
                boundary.ConnectionGeometry = (
                    self.file.createIfcConnectionSurfaceGeometry(curve_bounded_plane)
                )
                cell_index = cell.Get("index")
                if cell_index is not None:
                    # can't assign psets to an IfcRelationship, use Description instead
                    boundary.Description = "CellIndex " + str(cell_index)
                face_index = face.Get("index")
                if face_index is not None:
                    boundary.Name = "FaceIndex " + face_index
                boundaries.append(boundary)

            # representation

            if mywall.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # type (IfcVirtualElementType isn't valid)

            product_type = get_type_object(
                self.file,
                self.style_object,
                ifc_type=self.ifc + "Type",
                stylename=self.style,
                name=self.name,
            )
            api.type.assign_type(
                self.file,
                related_objects=[mywall],
                relating_type=product_type,
            )

            thickness = get_thickness(self.file, product_type)
            self.inner = thickness + self.offset

            # copy Usage from Type to Element
            for inverse in self.file.get_inverse(
                ifcopenshell.util.element.get_material(product_type)
            ):
                if inverse.is_a("IfcMaterialLayerSetUsage"):
                    inverse.OffsetFromReferenceLine = self.offset

            # mapping from normalised X-axis to this rotated axis
            matrix_forward = matrix_align(
                [*self.corner_coor(id_segment), 0.0],
                [*self.corner_coor(id_segment + 1), 0.0],
            )
            matrix_reverse = numpy.linalg.inv(matrix_forward)

            # outside face start and end coordinates
            v_out_a = self.corner_out(id_segment)
            v_out_b = self.corner_out(id_segment + 1)
            # inside face start and end coordinates
            v_in_a = self.corner_in(id_segment)
            v_in_b = self.corner_in(id_segment + 1)

            # wall is a plan shape extruded vertically
            solid = create_extruded_area_solid(
                self.file,
                [
                    transform(matrix_reverse, vertex)
                    for vertex in [v_in_a, v_out_a, v_out_b, v_in_b]
                ],
                self.height,
            )

            # FIXME use geometry.connect_path
            # Rel Connects Path Elements
            if previous_wall is None:
                first_wall = mywall
            else:
                rel_connects = api.root.create_entity(
                    self.file,
                    ifc_class="IfcRelConnectsPathElements",
                    name=self.name,
                )
                rel_connects.RelatingElement = mywall
                rel_connects.RelatingConnectionType = "ATSTART"
                rel_connects.RelatingPriorities = []
                rel_connects.ConnectionGeometry = (
                    self.file.createIfcConnectionCurveGeometry(
                        self.file.createIfcPolyline(
                            [
                                self.file.createIfcCartesianPoint(
                                    transform(matrix_reverse, v_in_a)
                                ),
                                self.file.createIfcCartesianPoint(
                                    transform(matrix_reverse, v_out_a)
                                ),
                            ]
                        ),
                        None,
                    )
                )
                rel_connects.RelatedElement = previous_wall
                rel_connects.RelatedConnectionType = "ATEND"
                rel_connects.RelatedPriorities = []
                rel_connects.Description = "MITRE"
            if self.closed and id_segment == len(self.path) - 1:
                rel_connects = api.root.create_entity(
                    self.file,
                    ifc_class="IfcRelConnectsPathElements",
                    name=self.name,
                )
                rel_connects.RelatingElement = mywall
                rel_connects.RelatingConnectionType = "ATEND"
                rel_connects.RelatingPriorities = []
                rel_connects.ConnectionGeometry = (
                    self.file.createIfcConnectionCurveGeometry(
                        self.file.createIfcPolyline(
                            [
                                self.file.createIfcCartesianPoint(
                                    transform(matrix_reverse, v_in_b)
                                ),
                                self.file.createIfcCartesianPoint(
                                    transform(matrix_reverse, v_out_b)
                                ),
                            ]
                        ),
                        None,
                    )
                )
                rel_connects.RelatedElement = first_wall
                rel_connects.RelatedConnectionType = "ATSTART"
                rel_connects.RelatedPriorities = []
                rel_connects.Description = "MITRE"
            previous_wall = mywall

            # axis is a straight line
            axis = self.file.createIfcPolyline(
                [
                    self.file.createIfcCartesianPoint(point)
                    for point in [
                        transform(matrix_reverse, vertex)
                        for vertex in [
                            self.corner_coor(id_segment),
                            self.corner_coor(id_segment + 1),
                        ]
                    ]
                ]
            )

            back_cell = self.chain.graph[segment[0]][1]["back_cell"]
            front_cell = self.chain.graph[segment[0]][1]["front_cell"]
            add_face_topology_epsets(self.file, mywall, face, back_cell, front_cell)

            # structure
            face_surface = create_face_surface(self.file, vertices, normal)
            # generate structural surfaces
            structural_surface = api.root.create_entity(
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.style + "/" + self.name,
                predefined_type="SHELL",
            )
            assignment = api.root.create_entity(self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [mywall]
            add_face_topology_epsets(
                self.file, structural_surface, face, back_cell, front_cell
            )
            structural_surface.Thickness = self.structural_thickness
            api.structural.assign_structural_analysis_model(
                self.file,
                product=structural_surface,
                structural_analysis_model=self.structural_analysis_model,
            )
            api.geometry.assign_representation(
                self.file,
                product=structural_surface,
                representation=self.file.createIfcTopologyRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Face",
                    [face_surface],
                ),
            )
            api.material.assign_material(
                self.file,
                products=[structural_surface],
                material=get_material_by_name(
                    self.file,
                    self.style_object,
                    name=self.structural_material,
                    stylename=self.style,
                ),
            )

            # clip the top of the wall if face isn't rectangular
            edges_ptr = []
            face.EdgesCrop(edges_ptr)
            for edge in edges_ptr:
                start_coor = transform(matrix_reverse, edge.StartVertex().Coordinates())
                end_coor = transform(matrix_reverse, edge.EndVertex().Coordinates())
                solid = clip_solid(
                    self.file,
                    solid,
                    subtract_3d(
                        start_coor,
                        [0.0, 0.0, self.elevation],
                    ),
                    subtract_3d(end_coor, [0.0, 0.0, self.elevation]),
                )
                # clip beyond the end of the wall if necessary
                if (
                    el(start_coor[2]) < el(self.elevation + self.height)
                    and distance_2d(
                        start_coor[0:2],
                        transform(matrix_reverse, self.corner_coor(id_segment + 1)),
                    )
                    < 0.001
                ):
                    solid = clip_solid(
                        self.file,
                        solid,
                        subtract_3d(
                            start_coor,
                            [0.0, 0.0, self.elevation],
                        ),
                        subtract_3d(
                            add_3d(start_coor, [1.0, 0.0, 0.0]),
                            [0.0, 0.0, self.elevation],
                        ),
                    )
                elif (
                    el(start_coor[2]) < el(self.elevation + self.height)
                    and distance_2d(
                        start_coor[0:2],
                        transform(matrix_reverse, self.corner_coor(id_segment)),
                    )
                    < 0.001
                ):
                    solid = clip_solid(
                        self.file,
                        solid,
                        subtract_3d(
                            start_coor,
                            [0.0, 0.0, self.elevation],
                        ),
                        subtract_3d(
                            add_3d(start_coor, [-1.0, 0.0, 0.0]),
                            [0.0, 0.0, self.elevation],
                        ),
                    )
                # clip beyond the start of the wall if necessary
                if (
                    el(end_coor[2]) < el(self.elevation + self.height)
                    and distance_2d(
                        end_coor[0:2],
                        transform(matrix_reverse, self.corner_coor(id_segment)),
                    )
                    < 0.001
                ):
                    solid = clip_solid(
                        self.file,
                        solid,
                        subtract_3d(
                            end_coor,
                            [0.0, 0.0, self.elevation],
                        ),
                        subtract_3d(
                            subtract_3d(end_coor, [1.0, 0.0, 0.0]),
                            [0.0, 0.0, self.elevation],
                        ),
                    )
                elif (
                    el(end_coor[2]) < el(self.elevation + self.height)
                    and distance_2d(
                        end_coor[0:2],
                        transform(matrix_reverse, self.corner_coor(id_segment + 1)),
                    )
                    < 0.001
                ):
                    solid = clip_solid(
                        self.file,
                        solid,
                        subtract_3d(
                            end_coor,
                            [0.0, 0.0, self.elevation],
                        ),
                        subtract_3d(
                            subtract_3d(end_coor, [-1.0, 0.0, 0.0]),
                            [0.0, 0.0, self.elevation],
                        ),
                    )

            if len(edges_ptr) == 0:
                representationtype = "SweptSolid"
            else:
                representationtype = "Clipping"

            shape = self.file.createIfcShapeRepresentation(
                body_context,
                body_context.ContextIdentifier,
                representationtype,
                [solid],
            )
            api.geometry.assign_representation(
                self.file,
                product=mywall,
                representation=shape,
            )

            shape = self.file.createIfcShapeRepresentation(
                axis_context,
                axis_context.ContextIdentifier,
                "Curve2D",
                [axis],
            )
            api.geometry.assign_representation(
                self.file,
                product=mywall,
                representation=shape,
            )
            api.geometry.edit_object_placement(
                self.file,
                product=mywall,
                matrix=matrix_forward
                @ matrix_align([0.0, 0.0, self.elevation], [1.0, 0.0, 0.0]),
            )

            segment = self.openings[id_segment]
            for id_opening in range(len(self.openings[id_segment])):
                db = self.get_family(segment[id_opening]["name"])
                opening = db["list"][segment[id_opening]["size"]]
                name = opening["name"]

                left, right = self.opening_coor(id_segment, id_opening)
                opening_offset = scale_2d(-self.offset, self.normal_segment(id_segment))
                left_2d = add_2d(left[0:2], opening_offset)
                right_2d = add_2d(right[0:2], opening_offset)

                if db["type"] == "window":
                    ifc_class = "IfcWindow"
                else:
                    ifc_class = "IfcDoor"
                entity = api.root.create_entity(
                    self.file,
                    ifc_class=ifc_class,
                    name=segment[id_opening]["name"],
                )
                add_face_topology_epsets(self.file, entity, face, back_cell, front_cell)
                # window/door width and height attributes can't be set in Type
                api.attribute.edit_attributes(
                    self.file,
                    product=entity,
                    attributes={
                        "OverallHeight": opening["height"],
                        "OverallWidth": opening["width"],
                    },
                )
                # place the entity in space
                api.geometry.edit_object_placement(
                    self.file,
                    product=entity,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # assign the entity to a storey
                assign_storey_byindex(self.file, entity, self.building, self.level)

                element_type = get_type_object(
                    self.file,
                    self.style_object,
                    ifc_type=ifc_class + "Type",
                    stylename=self.style,
                    name=name,
                )
                api.type.assign_type(
                    self.file,
                    related_objects=[entity],
                    relating_type=element_type,
                )

                # create an Opening to cut the wall

                myrepresentation = None

                # look for a Clearance representation in the Type

                for representation_map in element_type.RepresentationMaps:
                    if (
                        representation_map.MappedRepresentation.RepresentationIdentifier
                        == "Clearance"
                    ):
                        myrepresentation = self.file.createIfcShapeRepresentation(
                            body_context,
                            body_context.ContextIdentifier,
                            representation_map.MappedRepresentation.RepresentationType,
                            representation_map.MappedRepresentation.Items,
                        )

                if not myrepresentation:
                    # look for a Profile representation in the Type

                    swept_solid = None
                    profile = ifcopenshell.util.representation.get_representation(
                        element_type, "Model", "Profile", "ELEVATION_VIEW"
                    )

                    # create a SweptSolid from this Profile

                    if profile:
                        settings = ifcopenshell.geom.settings()
                        settings.set("dimensionality", ifcopenshell.ifcopenshell_wrapper.CURVES_SURFACES_AND_SOLIDS)
                        shape = ifcopenshell.geom.create_shape(settings, profile)
                        verts = shape.verts
                        edges = shape.edges
                        grouped_verts = [
                            [verts[i], verts[i + 1], verts[i + 2]]
                            for i in range(0, len(verts), 3)
                        ]
                        grouped_edges = [
                            [edges[i], edges[i + 1]] for i in range(0, len(edges), 2)
                        ]

                        edges_ptr = []
                        for edge in grouped_edges:
                            edges_ptr.append(
                                Edge.ByStartVertexEndVertex(
                                    Vertex.ByCoordinates(*grouped_verts[edge[0]]),
                                    Vertex.ByCoordinates(*grouped_verts[edge[1]]),
                                )
                            )
                        try:
                            myvertices = []
                            Face.ByEdges(edges_ptr).VerticesPerimeter(myvertices)
                            points = [vertex.Coordinates() for vertex in myvertices]
                            myprofile = create_closed_profile_from_points(
                                self.file, [[p[0], p[2]] for p in points]
                            )
                            swept_solid = self.file.createIfcExtrudedAreaSolid(
                                myprofile,
                                self.file.createIfcAxis2Placement3D(
                                    self.file.createIfcCartesianPoint(
                                        (0.0, -0.02, 0.0)
                                    ),
                                    self.file.createIfcDirection((0.0, -1.0, 0.0)),
                                    self.file.createIfcDirection((1.0, 0.0, 0.0)),
                                ),
                                self.file.createIfcDirection((0.0, 0.0, -1.0)),
                                thickness + 0.04,
                            )
                        except RuntimeError:
                            continue

                    if not swept_solid:
                        # create a SweptSolid from the window/door dimensions

                        inner = thickness + 0.02
                        outer = -0.02
                        swept_solid = create_extruded_area_solid(
                            self.file,
                            [
                                [0.0, outer],
                                [opening["width"], outer],
                                [opening["width"], inner],
                                [0.0, inner],
                            ],
                            opening["height"],
                        )

                    # use SweptSolid Representation

                    myrepresentation = self.file.createIfcShapeRepresentation(
                        body_context,
                        body_context.ContextIdentifier,
                        "SweptSolid",
                        [swept_solid],
                    )

                    # stuff this SweptSolid into the Type for use next time

                    clearance_representation = self.file.createIfcShapeRepresentation(
                        clearance_context,
                        clearance_context.ContextIdentifier,
                        "SweptSolid",
                        [swept_solid],
                    )
                    api.geometry.assign_representation(
                        self.file,
                        product=element_type,
                        representation=clearance_representation,
                    )

                myopening = api.root.create_entity(
                    self.file,
                    ifc_class="IfcOpeningElement",
                    name=element_type.Name,
                    predefined_type="OPENING",
                )
                api.geometry.assign_representation(
                    self.file,
                    product=myopening,
                    representation=myrepresentation,
                )

                # place the opening where the wall is

                api.geometry.edit_object_placement(
                    self.file,
                    product=myopening,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # use the opening to cut the wall, no need to assign a storey
                api.void.add_opening(self.file, opening=myopening, element=mywall)
                # # using the opening to cut the structural model isn't allowed
                # api.void.add_opening(
                #     self.file,
                #     opening=myopening,
                #     element=structural_surface,
                # )
                # associate the opening with our window
                api.void.add_filling(self.file, opening=myopening, element=entity)

                # openings are also space boundaries
                cill = self.elevation + db["cill"]
                soffit = cill + opening["height"]
                vertices = [
                    [*left[0:2], cill],
                    [*right[0:2], cill],
                    [*right[0:2], soffit],
                    [*left[0:2], soffit],
                ]
                cell_id = 0
                for cell in cells_ordered:
                    parent_boundary = boundaries[cell_id]
                    cell_id += 1
                    if cell is None:
                        continue
                    boundary = api.root.create_entity(
                        self.file,
                        ifc_class="IfcRelSpaceBoundary2ndLevel",
                    )
                    boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    boundary.InternalOrExternalBoundary = (
                        parent_boundary.InternalOrExternalBoundary
                    )
                    boundary.RelatedBuildingElement = entity
                    if cell == cells_ordered[0]:
                        # the face points to this cell
                        nodes_2d, matrix = map_to_2d_simple(
                            reversed(vertices), [-v for v in normal]
                        )
                    else:
                        nodes_2d, matrix = map_to_2d_simple(vertices, normal)

                    curve_bounded_plane = create_curve_bounded_plane(
                        self.file, nodes_2d, matrix
                    )
                    boundary.ConnectionGeometry = (
                        self.file.createIfcConnectionSurfaceGeometry(
                            curve_bounded_plane
                        )
                    )
                    boundary.Description = parent_boundary.Description
                    boundary.Name = parent_boundary.Name
                    boundary.ParentBoundary = parent_boundary

    def init_openings(self):
        """We need an array for openings the same size as wall segments array"""
        if not len(self.openings) == self.segments():
            self.openings = []
            for _ in range(self.segments()):
                self.openings.append([])

        # part may be a wall, add some openings
        if "do_populate_exterior_openings" in self.__dict__:
            edges = self.chain.edges()
            for id_segment in range(len(self.openings)):
                edge = self.chain.graph[edges[id_segment][0]]
                try:
                    interior_type = edge[1]["back_cell"].Usage()
                except AttributeError:
                    interior_type = "living"
                try:
                    exterior_type = edge[1]["front_cell"].Usage()
                except AttributeError:
                    exterior_type = None
                access = 0
                if exterior_type == "outside":
                    access = 1
                self.populate_exterior_openings(id_segment, interior_type, access)
                self.fix_heights(id_segment)
                self.fix_segment(id_segment)
                self.fix_gable(id_segment)
        elif "do_populate_interior_openings" in self.__dict__:
            edge = self.chain.graph[self.chain.edges()[0][0]]
            face = edge[1]["face"]
            vertex = face.GraphVertex(self.circulation)
            # FIXME determine door orientation using 'separation' attribute, see Molior.connect_spaces()
            if (
                vertex is not None
                and edge[1]["back_cell"] is not None
                and edge[1]["front_cell"] is not None
            ):
                self.populate_interior_openings(
                    0, edge[1]["back_cell"].Usage(), edge[1]["front_cell"].Usage(), 0
                )
                self.fix_heights(0)
                self.fix_segment(0)
                # TODO door location and account for gable headroom

    def opening_coor(self, id_segment, id_opening):
        """rectangle coordinates of an opening on the axis"""
        opening = self.openings[id_segment][id_opening]
        db = self.get_family(opening["name"])
        width = db["list"][opening["size"]]["width"]
        height = db["list"][opening["size"]]["height"]
        up = opening["up"]
        along = opening["along"]
        segment_direction = self.direction_segment(id_segment)

        bottom = self.elevation + up
        top = bottom + height

        A = add_2d(self.path[id_segment], scale_2d(along, segment_direction))
        B = add_2d(self.path[id_segment], scale_2d(along + width, segment_direction))

        return [A[0], A[1], bottom], [B[0], B[1], top]

    def populate_exterior_openings(self, id_segment, interior_type, access):
        """Add initial windows and doors to a segment"""
        if interior_type is None:
            self.openings[id_segment].append(
                {"name": "undefined outside window", "along": 0.5, "size": 0}
            )
        if interior_type in ("living", "retail"):
            self.openings[id_segment].append(
                {"name": "living outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "toilet":
            self.openings[id_segment].append(
                {"name": "toilet outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "kitchen":
            self.openings[id_segment].append(
                {"name": "kitchen outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "bedroom":
            self.openings[id_segment].append(
                {"name": "bedroom outside window", "along": 0.5, "size": 0}
            )
        if interior_type in ("circulation", "stair"):
            self.openings[id_segment].append(
                {"name": "circulation outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "retail" and self.level == 0:
            self.openings[id_segment].append(
                {"name": "retail entrance", "along": 0.5, "size": 0}
            )
        if interior_type in ("circulation", "stair") and self.level == 0:
            self.openings[id_segment].append(
                {"name": "house entrance", "along": 0.5, "size": 0}
            )
        if interior_type != "toilet" and access == 1:
            self.openings[id_segment].append(
                {"name": "living outside door", "along": 0.5, "size": 0}
            )

    def populate_interior_openings(self, id_segment, type_a, type_b, access):
        """Add an initial door to an interior segment"""
        self.openings[id_segment].append(
            {"name": "living inside door", "along": 0.5, "size": 0}
        )

    def get_family(self, usage):
        """Retrieve an family definition via the style"""
        if usage in self.style_openings:
            family = self.style_openings[usage]
            if family["name"] in self.style_families:
                return {
                    "list": self.style_families[family["name"]],
                    "type": family["type"],
                    "cill": family["cill"],
                }
        return {
            "list": [
                {
                    "name": "error",
                    "height": 1.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "name": "error",
                    "height": 2.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "name": "error",
                    "height": 2.0,
                    "width": 2.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "name": "error",
                    "height": 1.0,
                    "width": 2.0,
                    "side": 0.1,
                    "end": 0.0,
                },
            ],
            "type": "window",
            "cill": 1.0,
            "material": "Error",
        }

    def fix_heights(self, id_segment):
        """Top of openings need to be lower than ceiling soffit"""
        soffit = self.height - self.ceiling

        openings = self.openings[id_segment]
        openings_new = []

        for opening in openings:
            db = self.get_family(opening["name"])
            mylist = db["list"]
            opening["up"] = db["cill"]
            width_original = mylist[opening["size"]]["width"]

            # list heights of possible openings
            heights = []
            for index in range(len(mylist)):
                if not mylist[index]["width"] == width_original:
                    continue
                heights.append(mylist[index]["height"])

            # find the tallest height that fits, or shortest that doesn't fit
            heights.sort(reverse=True)
            for height in heights:
                best_height = height
                if best_height + opening["up"] <= soffit:
                    break

            # figure out which opening this is
            for index in range(len(mylist)):
                if mylist[index]["height"] == best_height:
                    opening["size"] = index

            # lower if we can if the top don't fit
            while (
                opening["up"] + mylist[opening["size"]]["height"] >= soffit
                and opening["up"] >= 0.15
            ):
                opening["up"] -= 0.15

            # put it in wall segment if top fits
            if opening["up"] + mylist[opening["size"]]["height"] <= soffit:
                openings_new.append(opening)

        self.openings[id_segment] = openings_new

    def fix_overlaps(self, id_segment):
        """openings don't want to overlap with each other"""
        openings = self.openings[id_segment]

        for id_opening in range(len(openings) - 1):
            # this opening has a width and side space
            opening = openings[id_opening]
            db = self.get_family(opening["name"])
            width = db["list"][opening["size"]]["width"]
            side = db["list"][opening["size"]]["side"]

            # how much side space does the next opening need
            opening_next = openings[id_opening + 1]
            db_next = self.get_family(opening_next["name"])
            side_next = db_next["list"][opening_next["size"]]["side"]

            # minimum allowable space between this opening and the next
            border = side
            if side_next > border:
                border = side_next

            # next opening needs to be at least this far along
            along_ok = opening["along"] + width + border
            if along_ok <= openings[id_opening + 1]["along"]:
                continue
            openings[id_opening + 1]["along"] = along_ok

    def fix_overrun(self, id_segment):
        """openings can't go past the end of the segment"""
        openings = self.openings[id_segment]

        # this is the furthest an opening can go
        length = self.length_segment(id_segment) - self.border(id_segment)[1]

        db_last = self.get_family(openings[-1]["name"])
        width_last = db_last["list"][openings[-1]["size"]]["width"]
        end_last = db_last["list"][openings[-1]["size"]]["end"]

        overrun = openings[-1]["along"] + width_last + end_last - length
        if overrun <= 0.0:
            return

        # slide all the openings back by amount of overrun
        for id_opening in range(len(openings)):
            openings[id_opening]["along"] -= overrun

    def fix_underrun(self, id_segment):
        """openings can't start before beginning of segment"""
        openings = self.openings[id_segment]

        db_first = self.get_family(openings[0]["name"])
        end_first = db_first["list"][openings[0]["size"]]["end"]

        underrun = self.border(id_segment)[0] + end_first - openings[0]["along"]
        if underrun <= 0.0:
            return

        # fix underrun by sliding all but last opening forward by no more than amount of underrun
        # or until spaced by border
        for id_opening in reversed(range(len(openings) - 1)):
            # this opening has a width and side space
            opening = openings[id_opening]
            db = self.get_family(opening["name"])
            width = db["list"][opening["size"]]["width"]
            side = db["list"][opening["size"]]["side"]

            # how much side space does the next opening need
            opening_next = openings[id_opening + 1]
            db_next = self.get_family(opening_next["name"])
            side_next = db_next["list"][opening_next["size"]]["side"]

            # minimum allowable space between this opening and the next
            border = side
            if side_next > border:
                border = side_next

            # this opening needs to be at least this far along
            along_ok = openings[id_opening + 1]["along"] - border - width
            if opening["along"] >= along_ok:
                continue

            slide = along_ok - opening["along"]
            if slide > underrun:
                slide = underrun
            opening["along"] += slide

    def border(self, id_segment):
        """set border distances if inside corners"""
        # walls are drawn anti-clockwise around the building,
        # the distance 'along' is from left-to-right as looking from outside
        border_left = 0.0
        border_right = 0.0

        # first segment in an open chain
        if not self.closed and id_segment == 0:
            border_left = self.inner
        else:
            angle_left = self.angle_segment(id_segment) - self.angle_segment(
                id_segment - 1
            )
            if angle_left < 0.0:
                angle_left += 360.0
            border_left = self.inner
            if angle_left > 135.0 and angle_left < 315.0:
                border_left = -self.offset

        # last segment in an open chain
        if not self.closed and id_segment == len(self.path) - 2:
            border_right = self.inner
        else:
            segment_right = id_segment + 1
            if segment_right == len(self.path):
                segment_right = 0
            angle_right = self.angle_segment(segment_right) - self.angle_segment(
                id_segment
            )
            if angle_right < 0.0:
                angle_right += 360.0
            border_right = self.inner
            if angle_right > 135.0 and angle_right < 315.0:
                border_right = -self.offset

        return (border_left, border_right)

    def length_openings(self, id_segment):
        """minimum wall length the currently defined openings require"""
        openings = self.openings[id_segment]
        if len(openings) == 0:
            return 0.0

        db_first = self.get_family(openings[0]["name"])
        end_first = db_first["list"][openings[0]["size"]]["end"]
        db_last = self.get_family(openings[-1]["name"])
        end_last = db_last["list"][openings[-1]["size"]]["end"]

        # start with end spacing
        length_openings = end_first + end_last
        # add width of all the openings
        for id_opening in range(len(openings)):
            db = self.get_family(openings[id_opening]["name"])
            width = db["list"][openings[id_opening]["size"]]["width"]
            length_openings += width

        # add wall between openings
        for id_opening in range(len(openings) - 1):
            if not len(openings) > 1:
                continue
            db = self.get_family(openings[id_opening]["name"])
            side = db["list"][openings[id_opening]["size"]]["side"]

            db_next = self.get_family(openings[id_opening + 1]["name"])
            side_next = db_next["list"][openings[id_opening + 1]["size"]]["side"]

            if side_next > side:
                side = side_next
            length_openings += side

        return length_openings

    def fix_segment(self, id_segment):
        openings = self.openings[id_segment]
        if len(openings) == 0:
            return

        # this is the space we can use to fit windows and doors
        length = (
            self.length_segment(id_segment)
            - self.border(id_segment)[0]
            - self.border(id_segment)[1]
        )

        # reduce multiple windows to one, multiple doors to one
        found_door = False
        found_window = False
        new_openings = []
        for opening in openings:
            db = self.get_family(opening["name"])
            if db["type"] == "door" and not found_door:
                new_openings.append(opening)
                found_door = True

            if db["type"] == "window" and not found_window:
                # set any window to narrowest of this height
                mylist = db["list"]
                height_original = mylist[opening["size"]]["height"]

                widths = {}
                for index in range(len(mylist)):
                    widths[index] = mylist[index]["width"]
                widest_dict = {
                    key: value
                    for key, value in sorted(widths.items(), key=lambda item: item[1])
                }
                widest = list(widest_dict.keys())
                widest.reverse()

                for size in widest:
                    if not mylist[size]["height"] == height_original:
                        continue
                    opening["size"] = size
                new_openings.append(opening)
                found_window = True

        self.openings[id_segment] = new_openings
        openings = new_openings

        # find a door, fit the widest of this height
        for opening in openings:
            db = self.get_family(opening["name"])
            if db["type"] == "door":
                mylist = db["list"]
                height_original = mylist[opening["size"]]["height"]

                widths = {}
                for index in range(len(mylist)):
                    widths[index] = mylist[index]["width"]
                widest_dict = {
                    key: value
                    for key, value in sorted(widths.items(), key=lambda item: item[1])
                }
                widest = list(widest_dict.keys())
                widest.reverse()

                for size in widest:
                    if not mylist[size]["height"] == height_original:
                        continue
                    opening["size"] = size

                    # this fits the widest door for the wall ignoring any window
                    end = mylist[size]["end"]
                    width = mylist[size]["width"]
                    if end + width + end < length:
                        break

        # find a window, fit the widest of this height
        for opening in openings:
            db = self.get_family(opening["name"])
            if db["type"] == "window":
                mylist = db["list"]
                height_original = mylist[opening["size"]]["height"]

                widths = {}
                for index in range(len(mylist)):
                    widths[index] = mylist[index]["width"]
                widest_dict = {
                    key: value
                    for key, value in sorted(widths.items(), key=lambda item: item[1])
                }
                widest = list(widest_dict.keys())
                widest.reverse()

                for size in widest:
                    if not mylist[size]["height"] == height_original:
                        continue
                    opening["size"] = size

                    if self.length_openings(id_segment) < length:
                        break

                # duplicate window if possible until filled
                self.openings[id_segment] = openings
                if length < 0.0:
                    break

                self.openings[id_segment][1:1] = [opening.copy(), opening.copy()]

                if self.length_openings(id_segment) > length:
                    self.openings[id_segment][1:2] = []

                if self.length_openings(id_segment) > length:
                    self.openings[id_segment][1:2] = []

        length_openings = self.length_openings(id_segment)

        if length_openings > length:
            if len(self.openings[id_segment]) == 1:
                self.openings[id_segment] = []
                return

            db_last = self.get_family(openings[-1]["name"])

            if db_last["type"] == "door":
                self.openings[id_segment].pop(0)
            else:
                self.openings[id_segment].pop()

            self.fix_segment(id_segment)
            return

        self.align_openings(id_segment)
        self.fix_overlaps(id_segment)
        self.fix_overrun(id_segment)
        self.fix_underrun(id_segment)
        return

    def align_openings(self, id_segment):
        """equally space openings along the wall"""
        if self.name == "interior":
            return
        openings = self.openings[id_segment]
        if len(openings) == 0:
            return
        length = self.length_segment(id_segment)
        module = length / len(openings)

        along = module / 2
        for id_opening in range(len(openings)):
            db = self.get_family(openings[id_opening]["name"])
            width = db["list"][openings[id_opening]["size"]]["width"]
            openings[id_opening]["along"] = along - (width / 2)
            along += module
        return

    def fix_gable(self, id_segment):
        """Shorten or delete openings that project above roofline"""
        openings = self.openings[id_segment]
        if len(openings) == 0:
            return
        segment = self.chain.edges()[id_segment]
        face = self.chain.graph[segment[0]][1]["face"]

        edges_ptr = []
        face.EdgesCrop(edges_ptr)
        if edges_ptr == []:
            # top of face is horizontal
            return

        bad_openings = []
        for id_opening in range(len(openings)):
            coors = self.opening_coor(id_segment, id_opening)
            left_top = Vertex.ByCoordinates(*coors[0][0:2], coors[1][2])
            right_top = Vertex.ByCoordinates(*coors[1])
            if not FaceUtility.IsInside(
                face, left_top, 0.001
            ) or not FaceUtility.IsInside(face, right_top, 0.001):
                # try and find a shorter window
                opening = openings[id_opening]
                db = self.get_family(opening["name"])
                mylist = db["list"]
                width_original = mylist[opening["size"]]["width"]
                height_original = mylist[opening["size"]]["height"]
                # list heights of possible openings
                heights = []
                lookup = {}
                for index in range(len(mylist)):
                    if not mylist[index]["width"] == width_original:
                        continue
                    lookup[mylist[index]["height"]] = index
                    if mylist[index]["height"] < height_original:
                        heights.append(mylist[index]["height"])
                if len(heights) > 0:
                    heights.sort(reverse=True)
                    self.openings[id_segment][id_opening]["size"] = lookup[heights[0]]
                    self.fix_gable(id_segment)
                    return
                else:
                    bad_openings.append(id_opening)
        bad_openings.reverse()
        for id_opening in bad_openings:
            self.openings[id_segment].pop(id_opening)
