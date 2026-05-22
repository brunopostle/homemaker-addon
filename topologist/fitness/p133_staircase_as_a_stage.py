"""133 STAIRCASE AS A STAGE

Problem: A staircase is not just a way of getting from one floor to another.
The stair is itself a space, a volume, a part of the building; and unless this
space is made to live, it will be dead.

Solution: Place the main staircase in a position which is central and visible.
Make it wide enough so that it functions as a room in itself — a room where
people stop and talk, a room which allows glimpses of the life of the building
through several floors at once.

Higher patterns:
- 129 COMMON AREAS AT THE HEART **
- 131 THE FLOW THROUGH ROOMS **

Lower patterns:
- 158 OPEN STAIRS *
- 195 STAIRCASE VOLUME **
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 133 STAIRCASE AS A STAGE"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "stair_usages": {"stair"},
            "common_usages": {"living", "kitchen", "dining", "hall", "foyer", "entrance"},
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score stair cells that share walls with common/living spaces"""
        if cell.Usage() not in self.settings["stair_usages"]:
            return 1.0

        faces_ptr = []
        cell.Faces(None, faces_ptr)
        common_area = 0.0
        total_internal_area = 0.0
        for face in faces_ptr:
            if not face.IsVertical():
                continue
            if not face.IsInternal(self.cellcomplex):
                continue
            area = FaceUtility.Area(face)
            total_internal_area += area
            adj_cells = [
                c
                for c in face.Cells_Cached(self.cellcomplex)
                if not c.IsSame(cell)
            ]
            if adj_cells and adj_cells[0].Usage() in self.settings["common_usages"]:
                common_area += area

        if total_internal_area == 0.0:
            return 1.0
        return 0.8 + 0.4 * (common_area / total_internal_area)
