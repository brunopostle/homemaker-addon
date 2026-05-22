"""190 CEILING HEIGHT VARIETY

Problem: A building in which the ceiling height is the same everywhere is
virtually dead, because it is unable to create the variation of spaces which
people need in order to feel comfortable.

Solution: Try to establish a continuous variation of ceiling heights, from the
low and intimate spaces (7 to 8 feet) to the more public high spaces (10 to
12 feet) and the intermediate spaces in between.

Higher patterns:
- 127 INTIMACY GRADIENT **
- 129 COMMON AREAS AT THE HEART *

Lower patterns:
- 191 THE SHAPE OF INDOOR SPACE **
- 195 STAIRCASE VOLUME **
- 196 CORNER DOORS *
"""


class Assessor:
    """An Assessor for 190 CEILING HEIGHT VARIETY"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "min_height_difference": 0.4,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score cells whose height differs from their neighbours"""
        if cell.IsOutside():
            return 1.0
        cell_height = cell.Height()
        if cell_height == 0.0:
            return 1.0

        faces_ptr = []
        cell.Faces(None, faces_ptr)
        neighbour_heights = []
        for face in faces_ptr:
            if not face.IsInternal(self.cellcomplex):
                continue
            adj = [
                c
                for c in face.Cells_Cached(self.cellcomplex)
                if not c.IsSame(cell) and not c.IsOutside()
            ]
            if adj:
                neighbour_heights.append(adj[0].Height())

        if not neighbour_heights:
            return 1.0

        threshold = self.settings["min_height_difference"]
        different = sum(
            1 for h in neighbour_heights if abs(h - cell_height) > threshold
        )
        return 1.0 + different / len(neighbour_heights)
