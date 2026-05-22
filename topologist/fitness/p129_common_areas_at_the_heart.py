"""129 COMMON AREAS AT THE HEART

Problem: No social group — whether a family, a work group, or a school group —
can survive without informal meetings between the members of the group. These
informal meetings are the glue which holds the group together.

Solution: Create a single common area for each social group. Locate it at the
centre of gravity of all the spaces the group uses, and in such a position
that the major entering paths pass tangent to it or through it.

Higher patterns:
- 127 INTIMACY GRADIENT **
- 128 INDOOR SUNLIGHT **

Lower patterns:
- 130 ENTRANCE ROOM **
- 131 THE FLOW THROUGH ROOMS **
- 139 FARMHOUSE KITCHEN **
- 147 COMMUNAL EATING *
- 179 ALCOVES **
- 181 THE FIRE *
- 182 EATING ATMOSPHERE **
"""

import math


class Assessor:
    """An Assessor for 129 COMMON AREAS AT THE HEART"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "common_usages": {"living", "kitchen", "dining", "hall", "foyer"},
            "distance_scale": 5.0,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score common rooms located near the centroid of all indoor spaces"""
        if cell.IsOutside():
            return 1.0
        usage = cell.Usage()
        if usage not in self.settings["common_usages"]:
            return 1.0

        cells_ptr = []
        self.cellcomplex.Cells(None, cells_ptr)
        inside_cells = [c for c in cells_ptr if not c.IsOutside()]
        if not inside_cells:
            return 1.0

        centroid_x = sum(c.Centroid().X() for c in inside_cells) / len(inside_cells)
        centroid_y = sum(c.Centroid().Y() for c in inside_cells) / len(inside_cells)

        cx = cell.Centroid().X()
        cy = cell.Centroid().Y()
        dist = math.sqrt((cx - centroid_x) ** 2 + (cy - centroid_y) ** 2)
        scale = self.settings["distance_scale"]
        return 1.2 / (1.0 + dist / scale)
