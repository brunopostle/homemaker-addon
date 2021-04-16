import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
import molior
from molior.geometry_2d import matrix_align, add_2d, scale_2d

run = ifcopenshell.api.run


class Wall(BaseClass):
    """A vertical wall, internal or external"""

    def __init__(self, args={}):
        super().__init__(args)
        self.bounds = []
        self.ceiling = 0.35
        self.closed = 0
        self.floor = 0.02
        self.openings = []
        self.path = []
        self.type = "molior-wall"
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.init_openings()

    def init_openings(self):
        if len(self.openings) == self.segments():
            return
        self.openings = []
        for index in range(self.segments()):
            self.openings.append([])

    def Ifc(self, ifc, context):
        """Generate some ifc"""
        style = molior.Molior.style
        segments = len(self.path)
        if not self.closed:
            segments -= 1

        for id_segment in range(segments):
            # outside face start and end coordinates
            v_out_a = self.corner_out(id_segment)
            v_out_b = self.corner_out(id_segment + 1)
            if not self.closed:
                if id_segment == 0:
                    v_out_a = add_2d(v_out_a, self.extension_start())
                elif id_segment == segments:
                    v_out_b = add_2d(v_out_b, self.extension_end())

            # inside face start and end coordinates
            v_in_a = self.corner_in(id_segment)
            v_in_b = self.corner_in(id_segment + 1)
            if not self.closed:
                if id_segment == 0:
                    v_in_a = add_2d(v_in_a, self.extension_start())
                elif id_segment == segments:
                    v_in_b = add_2d(v_in_b, self.extension_end())

            mywall = run("root.create_entity", ifc, ifc_class="IfcWall", name="My Wall")
            ifc.assign_storey_byindex(mywall, self.level)
            shape = ifc.createSweptSolid(
                context,
                [v_in_a, v_out_a, v_out_b, v_in_b],
                self.height,
            )
            run(
                "geometry.assign_representation",
                ifc,
                product=mywall,
                representation=shape,
            )
            run(
                "geometry.edit_object_placement",
                ifc,
                product=mywall,
                matrix=matrix_align([0.0, 0.0, self.elevation], [1.0, 0.0, 0.0]),
            )
            # TODO draw axis representation, IfcRelConnectsPathElements
            # TODO draw wall surfaces for boundaries
            segment = self.openings[id_segment]
            for id_opening in range(len(self.openings[id_segment])):
                start, end = self.opening_coor(id_segment, id_opening)
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
                    ifc,
                    ifc_class=ifc_class,
                    name=segment[id_opening]["name"],
                )
                # windows/doors have width and height attributes
                run(
                    "attribute.edit_attributes",
                    ifc,
                    product=entity,
                    attributes={
                        "OverallHeight": opening["height"],
                        "OverallWidth": opening["width"],
                    },
                )
                # place the entity in space
                run(
                    "geometry.edit_object_placement",
                    ifc,
                    product=entity,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # assign the entity to a storey
                ifc.assign_storey_byindex(entity, self.level)

                # load geometry from a DXF file and assign to the entity
                ifc.assign_representation_fromDXF(context, entity, self.style, dxf_path)

                # create an opening
                myopening = run(
                    "root.create_entity",
                    ifc,
                    ifc_class="IfcOpeningElement",
                    name="My Opening",
                )
                run(
                    "attribute.edit_attributes",
                    ifc,
                    product=myopening,
                    attributes={"PredefinedType": "OPENING"},
                )

                # give the opening a Body representation
                inner = self.inner + 0.02
                outer = 0 - self.outer - 0.02
                run(
                    "geometry.assign_representation",
                    ifc,
                    product=myopening,
                    representation=ifc.createSweptSolid(
                        context,
                        [
                            [0.0, outer],
                            [opening["width"], outer],
                            [opening["width"], inner],
                            [0.0, inner],
                        ],
                        opening["height"],
                    ),
                )
                # place the opening where the wall is
                run(
                    "geometry.edit_object_placement",
                    ifc,
                    product=myopening,
                    matrix=matrix_align(
                        [left_2d[0], left_2d[1], self.elevation + db["cill"]],
                        [right_2d[0], right_2d[1], 0.0],
                    ),
                )
                # use the opening to cut the wall, no need to assign a storey
                run("void.add_opening", ifc, opening=myopening, element=mywall)
                # associate the opening with our window
                run("void.add_filling", ifc, opening=myopening, element=entity)

    def opening_coor(self, id_segment, id_opening):
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

    def populate_exterior_openings(self, segment_id, interior_type, access):
        if interior_type == None:
            self.openings[segment_id].append(
                {"name": "undefined outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "living" or interior_type == "retail":
            self.openings[segment_id].append(
                {"name": "living outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "toilet":
            self.openings[segment_id].append(
                {"name": "toilet outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "kitchen":
            self.openings[segment_id].append(
                {"name": "kitchen outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "bedroom":
            self.openings[segment_id].append(
                {"name": "bedroom outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "circulation" or interior_type == "stair":
            self.openings[segment_id].append(
                {"name": "circulation outside window", "along": 0.5, "size": 0}
            )
        if interior_type == "retail" and self.level == 0:
            self.openings[segment_id].append(
                {"name": "retail entrance", "along": 0.5, "size": 0}
            )
        if interior_type == "circulation" and self.level == 0:
            self.openings[segment_id].append(
                {"name": "house entrance", "along": 0.5, "size": 0}
            )
        if interior_type != "toilet" and access == 1:
            self.openings[segment_id].append(
                {"name": "living outside door", "along": 0.5, "size": 0}
            )

    def populate_interior_openings(self, segment_id, type_a, type_b, access):
        self.openings[segment_id].append(
            {"name": "living inside door", "along": 0.5, "size": 0}
        )

    def get_opening(self, usage):
        style = molior.Molior.style.get(self.style)
        if usage in style["openings"]:
            opening = style["openings"][usage]
            if opening["name"] in style["assets"]:
                return {
                    "list": style["assets"][opening["name"]],
                    "type": opening["type"],
                    "cill": opening["cill"],
                }
        return {
            "list": [
                {
                    "file": "error1.dxf",
                    "height": 1.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error2.dxf",
                    "height": 2.0,
                    "width": 1.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error3.dxf",
                    "height": 2.0,
                    "width": 2.0,
                    "side": 0.1,
                    "end": 0.0,
                },
                {
                    "file": "error4.dxf",
                    "height": 1.0,
                    "width": 2.0,
                    "side": 0.1,
                    "end": 0.0,
                },
            ],
            "type": "window",
            "cill": 1.0,
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

        # fix underrun by sliding all but last opening forward by no more than amount of underrun or until spaced by border
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
