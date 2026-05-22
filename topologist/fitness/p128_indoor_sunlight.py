"""128 INDOOR SUNLIGHT

Problem: If the right rooms are facing south, a house feels light and sunny.
If the wrong rooms are facing south, the house feels dark and gloomy.

Solution: Place the most important rooms along the south edge of the
building, and spread the building out along an east-west axis. Fine-tune
the arrangement so that the rooms which you use most in the morning are
on the east; rooms you use most in the afternoon are on the west.

Higher patterns:
- 105 SOUTH FACING OUTDOORS **
- 107 WINGS OF LIGHT **
- 127 INTIMACY GRADIENT **

Lower patterns:
- 135 TAPESTRY OF LIGHT AND DARK *
- 159 LIGHT ON TWO SIDES OF EVERY ROOM **
- 199 SUNNY COUNTER *
- 238 FILTERED LIGHT *
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 128 INDOOR SUNLIGHT"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "important_usages": {"living", "kitchen", "dining", "study", "workshop"},
            "axis_threshold": 0.3,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score important rooms with south-facing external walls"""
        if cell.IsOutside():
            return 1.0
        usage = cell.Usage()
        if usage not in self.settings["important_usages"]:
            return 1.0

        faces_ptr = []
        cell.FacesVerticalExternal(self.cellcomplex, faces_ptr)
        if not faces_ptr:
            return 0.8

        threshold = self.settings["axis_threshold"]
        south_area = 0.0
        total_area = 0.0
        for face in faces_ptr:
            area = FaceUtility.Area(face)
            total_area += area
            # face.Normal() points toward outside; south wall has normal[1] < 0
            if face.Normal()[1] < -threshold:
                south_area += area

        if total_area == 0.0:
            return 1.0
        return 0.8 + 0.4 * (south_area / total_area)
