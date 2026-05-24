"""105 SOUTH FACING OUTDOORS

Problem: In all but tropical climates, people gravitate toward outdoor spaces
that receive sunlight and avoid those that are permanently shaded.

Solution: Always place outdoor spaces to the south of the buildings which
enclose them (northern hemisphere), or to the north (southern hemisphere),
so that the outdoor spaces are bathed in sunlight, not in permanent shade.

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
            "hemisphere": "north",
            "factors": {},
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score outdoor cells that sit on the sunny side of adjacent indoor spaces"""
        if not cell.IsOutside():
            return 1.0

        # Northern hemisphere: sun is to the south, so outdoor space should be
        # south of the building — face normal points south (normal[1] < 0).
        # Southern hemisphere: sun is to the north, so face normal points north
        # (normal[1] > 0).
        sign = -1.0 if self.settings["hemisphere"] == "north" else 1.0

        faces_ptr = []
        cell.Faces(None, faces_ptr)
        sunny_area = 0.0
        total_external_area = 0.0
        for face in faces_ptr:
            if not face.IsVertical():
                continue
            if not face.IsExternal(self.cellcomplex):
                continue
            area = FaceUtility.Area(face)
            total_external_area += area
            if face.Normal()[1] * sign < -0.3:
                sunny_area += area

        if total_external_area == 0.0:
            return 1.0
        return 1.0 + sunny_area / total_external_area
