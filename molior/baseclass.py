from math import pi

from molior.geometry import (
    add_2d,
    angle_2d,
    distance_2d,
    normalise_2d,
    points_2line,
    scale_2d,
    subtract_2d,
    line_intersection,
)

# FIXME rename this since it isn't a baseclass for hull-based elements


class BaseClass:
    """A generic building object"""

    def __init__(self, args={}):
        self.closed = 1
        self.elevation = 0.0
        self.extension = 0.0
        self.guid = "my building"
        self.height = 0.0
        self.inner = 0.08
        self.level = 0
        self.name = "base-class"
        self.outer = 0.25
        self.plot = "my plot"
        self.style = "default"
        for arg in args:
            self.__dict__[arg] = args[arg]

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
        if not self.closed and (index == len(self.path) - 1 or index == 0):
            coor = self.corner_coor(index)
            string = str(coor[0]) + "__" + str(coor[1]) + "__" + str(self.elevation)
            normal_map = self.normals[self.normal_set]
            if self.condition == "external" and string in normal_map:
                # we have a stashed normal for this corner
                line_mitre = points_2line(coor, add_2d(coor, normal_map[string]))
                if index == len(self.path) - 1:
                    return line_intersection(line_a, line_mitre)
                elif index == 0:
                    return line_intersection(line_b, line_mitre)

            if index == len(self.path) - 1:
                return add_2d(self.corner_coor(index), offset_a)
            elif index == 0:
                return add_2d(self.corner_coor(index), offset_b)

        # deal with non-end corners
        if abs(distance_2d([0.0, 0.0], subtract_2d(offset_a, offset_b))) < 0.0000000001:
            return add_2d(self.corner_coor(index), offset_a)

        return line_intersection(line_a, line_b)

    def corner_in(self, index):
        """offset inside corner"""
        return self.corner_offset(index, 0 - self.inner)

    def corner_out(self, index):
        """offset outside corner"""
        return self.corner_offset(index, self.outer)

    def extension_start(self):
        return scale_2d(self.direction_segment(0), 0 - self.extension)

    def extension_end(self):
        return scale_2d(self.direction_segment(-2), self.extension)
