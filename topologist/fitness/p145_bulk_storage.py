"""145 BULK STORAGE

Problem: In houses and work places there is always a need for bulk storage;
a place for things which are not in daily use but which must be kept. The
usual solutions in contemporary housing — cupboards, closets, attic — are
inadequate.

Solution: Make sure that in every building there is adequate bulk storage.
This means at least 15 to 20 per cent of the total floor area of the building,
in rooms where things can be stored easily, conveniently, and without being
buried.

Higher patterns:
- 129 COMMON AREAS AT THE HEART *

Lower patterns:
- 197 THICK WALLS **
- 198 CLOSETS BETWEEN ROOMS **
- 200 OPEN SHELVES **
"""


class Assessor:
    """An Assessor for 145 BULK STORAGE"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "storage_usages": {"storage", "store", "utility", "pantry", "cellar", "attic"},
            "target_ratio": 0.15,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score the building's storage provision as a fraction of total floor area"""
        if cell.IsOutside():
            return 1.0

        cells_ptr = []
        self.cellcomplex.Cells(None, cells_ptr)

        total_area = sum(
            c.PlanArea() for c in cells_ptr if not c.IsOutside()
        )
        storage_area = sum(
            c.PlanArea()
            for c in cells_ptr
            if c.Usage() in self.settings["storage_usages"]
        )

        if total_area == 0.0:
            return 1.0
        actual_ratio = storage_area / total_area
        target = self.settings["target_ratio"]
        return min(actual_ratio / target, 1.2)
