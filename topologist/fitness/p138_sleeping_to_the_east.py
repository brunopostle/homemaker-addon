"""138 SLEEPING TO THE EAST

Problem: Bedrooms for people who sleep in them at night and get up in the
morning need eastern light to help them wake up naturally.

Solution: Give the bedroom an eastern orientation, so that it gets the
morning sun to help wake the sleepers. This means the bedroom windows, and
the long axis of the bedroom, should face east.

Higher patterns:
- 127 INTIMACY GRADIENT **
- 128 INDOOR SUNLIGHT **

Lower patterns:
- 136 COUPLE'S REALM *
- 143 BED CLUSTER *
- 188 BED ALCOVE *
"""

from topologic_core import FaceUtility


class Assessor:
    """An Assessor for 138 SLEEPING TO THE EAST"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "bedroom_usages": {"bedroom", "sleeping"},
            "axis_threshold": 0.3,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score bedroom cells that have east-facing external walls"""
        if cell.IsOutside():
            return 1.0
        if cell.Usage() not in self.settings["bedroom_usages"]:
            return 1.0

        faces_ptr = []
        cell.FacesVerticalExternal(self.cellcomplex, faces_ptr)
        if not faces_ptr:
            return 0.8

        threshold = self.settings["axis_threshold"]
        east_area = 0.0
        total_area = 0.0
        for face in faces_ptr:
            area = FaceUtility.Area(face)
            total_area += area
            # face.Normal() points toward outside; east wall has normal[0] > 0
            if face.Normal()[0] > threshold:
                east_area += area

        if total_area == 0.0:
            return 1.0
        return 0.8 + 0.4 * (east_area / total_area)
