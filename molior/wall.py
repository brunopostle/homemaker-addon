import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass


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

    def populate_exterior_openings(self, segment_id, interior_type, access):
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

        # say STDERR "Id: $id_segment, Length: $length, Openings: $length_openings";

        self.align_openings(id_segment)
        self.fix_overlaps(id_segment)
        self.fix_overrun(id_segment)
        self.fix_underrun(id_segment)
        return

    def align_openings(self, id_segment):
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
