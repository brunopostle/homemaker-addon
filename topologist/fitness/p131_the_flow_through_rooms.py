"""131 THE FLOW THROUGH ROOMS

Problem: The movement between rooms is as important as the rooms themselves;
and its arrangement has as much effect on social interaction in the rooms, as
the interiors of the rooms.

Solution: As far as possible, avoid the use of corridors and passages. Instead,
use public rooms and common rooms as rooms for movement and for gathering.
In a house, arrange the common rooms, one after another, so that they form a
chain or loop, which people naturally walk through.

Higher patterns:
- 127 INTIMACY GRADIENT **
- 129 COMMON AREAS AT THE HEART **

Lower patterns:
- 130 ENTRANCE ROOM **
- 132 SHORT PASSAGES **
- 141 A ROOM OF ONE'S OWN **
- 196 CORNER DOORS **
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 131 THE FLOW THROUGH ROOMS"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "corridor_usages": {"corridor", "circulation", "passage", "hallway"},
            "flow_usages": {"living", "kitchen", "dining", "hall", "foyer"},
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Penalise corridors; reward common rooms that form circulation chains"""
        usage = cell.Usage()
        if cell.IsOutside():
            return 1.0

        if usage in self.settings["corridor_usages"]:
            return 0.5

        if usage not in self.settings["flow_usages"]:
            return 1.0

        # Count distinct adjacent usages via internal vertical faces
        faces_ptr = []
        cell.Faces(None, faces_ptr)
        adjacent_usages = set()
        for face in faces_ptr:
            if not face.IsVertical():
                continue
            if not face.IsInternal(self.cellcomplex):
                continue
            adj_cells = [
                c
                for c in face.Cells_Cached(self.cellcomplex)
                if not c.IsSame(cell)
            ]
            if adj_cells:
                adjacent_usages.add(adj_cells[0].Usage())

        # A flow room connecting two or more distinct spaces is good
        n = len(adjacent_usages)
        if n >= 2:
            return 1.0 + n * 0.1
        return 1.0
