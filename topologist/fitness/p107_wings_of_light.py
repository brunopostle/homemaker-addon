"""107 WINGS OF LIGHT

Problem: Modern buildings are often so deep that their interior rooms are far
from any external wall, requiring permanent artificial lighting and cutting
occupants off from daylight and the outdoor world.

Solution: Divide every building into wings, with each wing narrow enough that
no point is more than 12 feet (3.6m) from an outside wall. Never make a wing
more than 25 feet (7.6m) wide.

Higher patterns:
- 105 SOUTH FACING OUTDOORS **
- 109 LONG THIN HOUSE *

Lower patterns:
- 128 INDOOR SUNLIGHT **
- 159 LIGHT ON TWO SIDES OF EVERY ROOM **
- 162 NORTH FACE *
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 107 WINGS OF LIGHT"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "good_factor": 1.2,
            "poor_factor": 0.8,
            "axis_threshold": 0.3,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score cells that have external walls on two roughly opposite sides"""
        if cell.IsOutside():
            return 1.0

        faces_ptr = []
        cell.FacesVerticalExternal(self.cellcomplex, faces_ptr)
        if not faces_ptr:
            return self.settings["poor_factor"]

        threshold = self.settings["axis_threshold"]
        has_north = any(f.Normal()[1] > threshold for f in faces_ptr)
        has_south = any(f.Normal()[1] < -threshold for f in faces_ptr)
        has_east = any(f.Normal()[0] > threshold for f in faces_ptr)
        has_west = any(f.Normal()[0] < -threshold for f in faces_ptr)

        if (has_north and has_south) or (has_east and has_west):
            return self.settings["good_factor"]
        return self.settings["poor_factor"]
