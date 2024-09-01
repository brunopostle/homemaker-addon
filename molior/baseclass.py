from math import pi

from .geometry import (
    add_2d,
    angle_2d,
    distance_2d,
    normalise_2d,
    points_2line,
    scale_2d,
    subtract_2d,
    line_intersection,
)
from .ifc import add_pset


class BaseClass:
    """A generic building object"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        self.do_representation = True
        self.elevation = 0.0
        self.extension = 0.0
        self.guid = "my building"
        self.height = 0.0
        self.inner = 0.08
        self.level = 0
        self.name = "base-class"
        self.offset = -0.25
        self.parent_aggregate = None
        self.plot = "my plot"
        self.psets = {}
        self.style = "default"
        self.file = None
        self.ifc = "IfcBuildingElementProxy"
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.identifier = self.style + "/" + self.name

    def add_psets(self, product):
        """self.psets is a dictionary of Psets, add them to an Ifc product"""
        for name, properties in self.psets.items():
            add_pset(self.file, product, name, properties)


class TraceClass(BaseClass):
    """A building object that follows a path"""

    def segments(self):
        """Number of segments in the path taking account for being closed or not"""
        segments = len(self.path)
        if not self.closed:
            segments -= 1
        return segments

    def length_segment(self, index):
        """Distance between vertices of this segment"""
        return distance_2d(self.corner_coor(index), self.corner_coor(index + 1))

    def angle_segment(self, index):
        """Angle of segment, degrees anticlockwise from 'east'"""
        return angle_2d(self.corner_coor(index), self.corner_coor(index + 1)) * 180 / pi

    def direction_segment(self, index):
        """Normalised 2D direction vector of segment"""
        return normalise_2d(
            subtract_2d(self.corner_coor(index + 1), self.corner_coor(index))
        )

    def normal_segment(self, index):
        """2D normal right-hand side"""
        vector = self.direction_segment(index)
        return [vector[1], 0 - vector[0]]

    def corner_coor(self, index):
        """2D coordinates of a corner"""
        while index >= len(self.path):
            index -= len(self.path)
        while index < 0:
            index += len(self.path)
        return self.path[index]

    def clipping_plane(self, index):
        """A plane defined by x, y & z directions and a point on the plane"""
        mitre = normalise_2d(
            add_2d(self.normal_segment(index), self.normal_segment(index - 1))
        )
        coor = self.corner_coor(index)
        return [
            [mitre[0], 0.0, mitre[1], coor[0]],
            [mitre[1], 0.0, -mitre[0], coor[1]],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]

    def corner_offset(self, index, distance):
        """2D coordinates of a corner offset by an arbitrary distance"""
        offset_a = scale_2d(distance, self.normal_segment(index - 1))
        offset_b = scale_2d(distance, self.normal_segment(index))

        # line equations of offset edges
        line_a = points_2line(
            add_2d(self.corner_coor(index - 1), offset_a),
            add_2d(self.corner_coor(index), offset_a),
        )
        line_b = points_2line(
            add_2d(self.corner_coor(index), offset_b),
            add_2d(self.corner_coor(index + 1), offset_b),
        )

        # deal with ends of open paths
        if not self.closed and index in (len(self.path) - 1, 0):
            coor = self.corner_coor(index)
            string = str(coor[0]) + "__" + str(coor[1]) + "__" + str(self.elevation)
            if self.normal_set in self.normals:
                normal_map = self.normals[self.normal_set]
                if self.condition == "external" and string in normal_map:
                    # we have a stashed normal for this corner
                    line_mitre = points_2line(coor, add_2d(coor, normal_map[string]))
                    if index == len(self.path) - 1:
                        return line_intersection(line_a, line_mitre)
                    if index == 0:
                        return line_intersection(line_b, line_mitre)

            if index == len(self.path) - 1:
                return add_2d(self.corner_coor(index), offset_a)
            if index == 0:
                return add_2d(self.corner_coor(index), offset_b)

        # deal with non-end corners
        if abs(distance_2d([0.0, 0.0], subtract_2d(offset_a, offset_b))) < 0.0000000001:
            return add_2d(self.corner_coor(index), offset_a)

        return line_intersection(line_a, line_b)

    def corner_in(self, index):
        """offset inside corner"""
        return self.corner_offset(index, -self.inner)

    def corner_out(self, index):
        """offset outside corner"""
        return self.corner_offset(index, -self.offset)

    def extension_start(self):
        """extend the start of an open path"""
        extension = self.extension
        if self.length_segment(0) + extension < 0:
            extension = -self.length_segment(0)
        return scale_2d(self.direction_segment(0), -extension)

    def extension_end(self):
        """extend the end of an open path"""
        extension = self.extension
        if self.length_segment(0) + extension < 0:
            extension = -self.length_segment(0)
        return scale_2d(self.direction_segment(-2), extension)
