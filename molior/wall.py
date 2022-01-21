import ifcopenshell.api
import numpy

from topologic import Vertex, FaceUtility
from topologist.helpers import el
import molior
from molior.baseclass import TraceClass
from molior.geometry import (
    matrix_align,
    add_2d,
    scale_2d,
    distance_2d,
    subtract_3d,
    add_3d,
    transform,
    map_to_2d,
)
from molior.ifc import (
    create_extruded_area_solid,
    clip_solid,
    create_face_surface,
    assign_representation_fromDXF,
    assign_storey_byindex,
    get_material_by_name,
    create_curve_bounded_plane,
)

run = ifcopenshell.api.run


class Wall(TraceClass):
    """A vertical wall, internal or external"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.bounds = []
        self.ceiling = 0.35
        self.closed = 0
        self.floor = 0.02
        self.ifc = "IfcWall"
        self.predefined_type = "SOLIDWALL"
        self.layerset = [[0.3, "Masonry"], [0.03, "Plaster"]]
        self.structural_material = "Masonry"
        self.opening_material = "Timber"
        self.openings = []
        self.path = []
        self.type = "molior-wall"
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]
        self.inner = self.thickness - self.outer
        self.identifier = self.style + "/" + self.name

    def execute(self):
        """Generate some ifc"""
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
            if item.ContextIdentifier == "Reference":
                reference_context = item
            if item.ContextIdentifier == "Body":
                body_context = item
            if item.ContextIdentifier == "Axis":
                axis_context = item
        self.init_openings()
        style = molior.Molior.style

        # traces have one or more segments, aggregate them
        aggregate = run(
            "root.create_entity",
            self.file,
            ifc_class=self.ifc,
            name=self.identifier,
        )
        assign_storey_byindex(self.file, aggregate, self.level)

        previous_wall = None
        segments = self.segments()
        for id_segment in range(segments):
            mywall = run(
                "root.create_entity",
                self.file,
                ifc_class=self.ifc,
                name=self.identifier,
            )
            run(
                "aggregate.assign_object",
                self.file,
                product=mywall,
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
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
            curve_bounded_plane = create_curve_bounded_plane(
                self.file, nodes_2d, matrix
            )
            for cell in face.CellsOrdered(self.cellcomplex):
                if cell == None:
                    boundaries.append(None)
                    continue
                boundary = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcRelSpaceBoundary2ndLevel",
                )
                if face.IsInternal(self.cellcomplex):
                    boundary.InternalOrExternalBoundary = "INTERNAL"
                else:
                    boundary.InternalOrExternalBoundary = "EXTERNAL"
                if mywall.is_a("IfcVirtualElement"):
                    boundary.PhysicalOrVirtualBoundary = "VIRTUAL"
                else:
                    boundary.PhysicalOrVirtualBoundary = "PHYSICAL"

                boundary.RelatedBuildingElement = mywall
                boundary.ConnectionGeometry = (
                    self.file.createIfcConnectionSurfaceGeometry(curve_bounded_plane)
                )
                cell_index = cell.Get("index")
                if not cell_index == None:
                    # can't assign psets to an IfcRelationship, use Description instead
                    boundary.Description = "CellIndex " + str(cell_index)
                boundaries.append(boundary)

            if mywall.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # reuse (or create) a Type
            myelement_type = self.get_element_type()
            run(
                "type.assign_type",
                self.file,
                related_object=mywall,
                relating_type=myelement_type,
            )
            self.add_psets(myelement_type)

            # Usage isn't created until after type.assign_type
            for inverse in self.file.get_inverse(
                ifcopenshell.util.element.get_material(myelement_type)
            ):
                if inverse.is_a("IfcMaterialLayerSetUsage"):
                    inverse.OffsetFromReferenceLine = 0.0 - self.outer

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

            # Rel Connects Path Elements
            if previous_wall == None:
                first_wall = mywall
            else:
                rel_connects = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcRelConnectsPathElements",
                    name=self.identifier,
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
            if self.closed and id_segment == len(self.path) - 1:
                rel_connects = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcRelConnectsPathElements",
                    name=self.identifier,
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
            self.add_topology_pset(mywall, face, back_cell, front_cell)

            # structure
            face_surface = create_face_surface(self.file, vertices, normal)
            # generate structural surfaces
            structural_surface = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.identifier,
                predefined_type="SHELL",
            )
            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [mywall]
            self.add_topology_pset(structural_surface, face, back_cell, front_cell)
            structural_surface.Thickness = self.thickness
            run(
                "structural.assign_structural_analysis_model",
                self.file,
                product=structural_surface,
                structural_analysis_model=self.file.by_type(
                    "IfcStructuralAnalysisModel"
                )[0],
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=structural_surface,
                representation=self.file.createIfcTopologyRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Face",
                    [face_surface],
                ),
            )
            run(
                "material.assign_material",
                self.file,
                product=structural_surface,
                material=get_material_by_name(
                    self.file,
                    reference_context,
                    self.structural_material,
                    self.style_materials,
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
            run(
                "geometry.assign_representation",
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
            run(
                "geometry.assign_representation",
                self.file,
                product=mywall,
                representation=shape,
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=mywall,
                matrix=matrix_forward
                @ matrix_align([0.0, 0.0, self.elevation], [1.0, 0.0, 0.0]),
            )

            segment = self.openings[id_segment]
            for id_opening in range(len(self.openings[id_segment])):
                db = self.get_opening(segment[id_opening]["name"])
                opening = db["list"][segment[id_opening]["size"]]
                filename = opening["file"]
                dxf_path = style.get_file(self.style, filename)

                l, r = self.opening_coor(id_segment, id_opening)
                left_2d = l[0:2]
                right_2d = r[0:2]

                if db["type"] == "window":
                    ifc_class = "IfcWindow"
                else:
                    ifc_class = "IfcDoor"
                entity = run(
                    "root.create_entity",
                    self.file,
                    ifc_class=ifc_class,
                    name=segment[id_opening]["name"],
                )
                self.add_topology_pset(entity, face, back_cell, front_cell)
                # window/door width and height attributes can't be set in Type
                run(
                    "attribute.edit_attributes",
                    self.file,
                    product=entity,
                    attributes={
                        "OverallHeight": opening["height"],
                        "OverallWidth": opening["width"],
                    },
                )
                # place the entity in space
                run(
                    "geometry.edit_object_placement",
                    self.file,
                    product=entity,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # assign the entity to a storey
                assign_storey_byindex(self.file, entity, self.level)
                # assign a material
                run(
                    "material.assign_material",
                    self.file,
                    product=entity,
                    material=get_material_by_name(
                        self.file, body_context, db["material"], self.style_materials
                    ),
                )
                # load geometry from a DXF file and assign to the entity
                assign_representation_fromDXF(
                    self.file, body_context, entity, self.style, dxf_path
                )

                # create an opening
                myopening = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcOpeningElement",
                    name="My Opening",
                    predefined_type="OPENING",
                )

                # give the opening a Body representation
                # TODO IFC library objects may come with a more complex opening shape
                inner = self.inner + 0.02
                outer = 0 - self.outer - 0.02
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=myopening,
                    representation=self.file.createIfcShapeRepresentation(
                        body_context,
                        body_context.ContextIdentifier,
                        "SweptSolid",
                        [
                            create_extruded_area_solid(
                                self.file,
                                [
                                    [0.0, outer],
                                    [opening["width"], outer],
                                    [opening["width"], inner],
                                    [0.0, inner],
                                ],
                                opening["height"],
                            )
                        ],
                    ),
                )
                # place the opening where the wall is
                run(
                    "geometry.edit_object_placement",
                    self.file,
                    product=myopening,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # use the opening to cut the wall, no need to assign a storey
                run("void.add_opening", self.file, opening=myopening, element=mywall)
                # # using the opening to cut the structural model isn't allowed
                # run(
                #     "void.add_opening",
                #     self.file,
                #     opening=myopening,
                #     element=structural_surface,
                # )
                # associate the opening with our window
                run("void.add_filling", self.file, opening=myopening, element=entity)

                # openings are also space boundaries
                cill = self.elevation + db["cill"]
                soffit = cill + opening["height"]
                vertices = [
                    [*left_2d, cill],
                    [*right_2d, cill],
                    [*right_2d, soffit],
                    [*left_2d, soffit],
                ]
                nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
                curve_bounded_plane = create_curve_bounded_plane(
                    self.file, nodes_2d, matrix
                )
                cell_id = 0
                for cell in face.CellsOrdered(self.cellcomplex):
                    parent_boundary = boundaries[cell_id]
                    cell_id += 1
                    if cell == None:
                        continue
                    boundary = run(
                        "root.create_entity",
                        self.file,
                        ifc_class="IfcRelSpaceBoundary2ndLevel",
                    )
                    boundary.PhysicalOrVirtualBoundary = "PHYSICAL"
                    boundary.InternalOrExternalBoundary = (
                        parent_boundary.InternalOrExternalBoundary
                    )
                    boundary.RelatedBuildingElement = entity
                    boundary.ConnectionGeometry = (
                        self.file.createIfcConnectionSurfaceGeometry(
                            curve_bounded_plane
                        )
                    )
                    boundary.Description = parent_boundary.Description
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
                face = edge[1]["face"]
                try:
                    interior_type = edge[1]["back_cell"].Usage()
                except:
                    interior_type = None
                try:
                    exterior_type = edge[1]["front_cell"].Usage()
                except:
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
            # FIXME determine door orientation
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
        db = self.get_opening(opening["name"])
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

    def get_opening(self, usage):
        """Retrieve an opening definition via the style"""
        if usage in self.style_openings:
            opening = self.style_openings[usage]
            if opening["name"] in self.style_assets:
                opening_material = self.opening_material
                if "material" in opening:
                    opening_material = opening["material"]
                return {
                    "list": self.style_assets[opening["name"]],
                    "type": opening["type"],
                    "cill": opening["cill"],
                    "material": opening_material,
                }
        return {
            "list": [
                {
                    "file": "error.dxf",
                    "height": 1.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error.dxf",
                    "height": 2.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error.dxf",
                    "height": 2.0,
                    "width": 2.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error.dxf",
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
            db = self.get_opening(opening["name"])
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
            db = self.get_opening(opening["name"])
            width = db["list"][opening["size"]]["width"]
            side = db["list"][opening["size"]]["side"]

            # how much side space does the next opening need
            opening_next = openings[id_opening + 1]
            db_next = self.get_opening(opening_next["name"])
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

        db_last = self.get_opening(openings[-1]["name"])
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

        db_first = self.get_opening(openings[0]["name"])
        end_first = db_first["list"][openings[0]["size"]]["end"]

        underrun = self.border(id_segment)[0] + end_first - openings[0]["along"]
        if underrun <= 0.0:
            return

        # fix underrun by sliding all but last opening forward by no more than amount of underrun
        # or until spaced by border
        for id_opening in reversed(range(len(openings) - 1)):
            # this opening has a width and side space
            opening = openings[id_opening]
            db = self.get_opening(opening["name"])
            width = db["list"][opening["size"]]["width"]
            side = db["list"][opening["size"]]["side"]

            # how much side space does the next opening need
            opening_next = openings[id_opening + 1]
            db_next = self.get_opening(opening_next["name"])
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
                border_left = self.outer

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
                border_right = self.outer

        return (border_left, border_right)

    def length_openings(self, id_segment):
        """minimum wall length the currently defined openings require"""
        openings = self.openings[id_segment]
        if len(openings) == 0:
            return 0.0

        db_first = self.get_opening(openings[0]["name"])
        end_first = db_first["list"][openings[0]["size"]]["end"]
        db_last = self.get_opening(openings[-1]["name"])
        end_last = db_last["list"][openings[-1]["size"]]["end"]

        # start with end spacing
        length_openings = end_first + end_last
        # add width of all the openings
        for id_opening in range(len(openings)):
            db = self.get_opening(openings[id_opening]["name"])
            width = db["list"][openings[id_opening]["size"]]["width"]
            length_openings += width

        # add wall between openings
        for id_opening in range(len(openings) - 1):
            if not len(openings) > 1:
                continue
            db = self.get_opening(openings[id_opening]["name"])
            side = db["list"][openings[id_opening]["size"]]["side"]

            db_next = self.get_opening(openings[id_opening + 1]["name"])
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
            db = self.get_opening(opening["name"])
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
            db = self.get_opening(opening["name"])
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
            db = self.get_opening(opening["name"])
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

            db_last = self.get_opening(openings[-1]["name"])

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
            db = self.get_opening(openings[id_opening]["name"])
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
                db = self.get_opening(opening["name"])
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
