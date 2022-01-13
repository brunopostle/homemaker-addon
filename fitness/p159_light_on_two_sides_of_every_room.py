"""159 LIGHT ON TWO SIDES OF EVERY ROOM

Problem: When they have a choice, people will always gravitate to those rooms
which have light on two sides, and leave the rooms which are lit only from one
side unused and empty.

Solution: Locate each room so that it has outdoor space outside it on at least
two sides, and then place windows in these outdoor walls so that natural light
falls into every room from more than one direction.

Higher patterns:
- 106 POSITIVE OUTDOOR SPACE **
- 107 WINGS OF LIGHT **
- 109 LONG THIN HOUSE *

Lower patterns:
- 106 POSITIVE OUTDOOR SPACE **
- 180 WINDOW PLACE **
- 192 WINDOWS OVERLOOKING LIFE *
- 209 ROOF LAYOUT *
- 221 NATURAL DOORS AND WINDOWS **
- 223 DEEP REVEALS
- 238 FILTERED LIGHT *
"""

from topologic import FaceUtility


class Assessor:
    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "windowless_styles": ["blank", "party"],
            "factors": {"living": 1.2, "kitchen": 1.2},
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """'crinkliness' is external wall area / floor area"""
        plan_area = cell.PlanArea()
        external_wall_area = self.external_wall_area(cell)
        if plan_area <= 0.0:
            return 1.0
        # is cell open to the sky
        if cell.IsOutside():
            cells_above = []
            cell.CellsAbove(self.cellcomplex, cells_above)
            if cells_above and cells_above[0].IsOutside():
                return 1.0
            elif not cells_above:
                return 1.0
        factor = 1.2
        usage = cell.Usage()
        if usage in self.settings["factors"]:
            factor = self.settings["factors"][usage]
        return factor * external_wall_area / plan_area

    def external_wall_area(self, cell):
        result = 0.0
        faces_ptr = []
        cell.FacesVerticalExternal(self.cellcomplex, faces_ptr)
        # external walls only count if they can fit windows
        for face in faces_ptr:
            if face.Get("stylename") in self.settings["windowless_styles"]:
                continue
            result += FaceUtility.Area(face)
        return result
