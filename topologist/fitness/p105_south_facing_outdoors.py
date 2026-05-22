"""105 SOUTH FACING OUTDOORS

Problem: In all but tropical climates, people gravitate toward outdoor spaces
that receive sunlight and avoid those that are permanently shaded.

Solution: Always place outdoor spaces to the south of the buildings which
enclose them, so that the outdoor spaces are bathed in sunlight, not north-
facing shade.

Higher patterns:
- 104 SITE REPAIR *
- 106 POSITIVE OUTDOOR SPACE **
- 107 WINGS OF LIGHT **

Lower patterns:
- 106 POSITIVE OUTDOOR SPACE **
- 128 INDOOR SUNLIGHT **
- 161 SUNNY PLACE *
- 162 NORTH FACE *
- 238 FILTERED LIGHT *
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 105 SOUTH FACING OUTDOORS"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "factors": {},
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score outdoor cells that sit to the south of adjacent indoor spaces"""
        if not cell.IsOutside():
            return 1.0

        faces_ptr = []
        cell.Faces(None, faces_ptr)
        south_area = 0.0
        total_external_area = 0.0
        for face in faces_ptr:
            if not face.IsVertical():
                continue
            if not face.IsExternal(self.cellcomplex):
                continue
            area = FaceUtility.Area(face)
            total_external_area += area
            # face.Normal() points outward from the building mass (toward outside)
            # when normal[1] < 0 the outside cell is to the south
            if face.Normal()[1] < -0.3:
                south_area += area

        if total_external_area == 0.0:
            return 1.0
        return 1.0 + south_area / total_external_area
