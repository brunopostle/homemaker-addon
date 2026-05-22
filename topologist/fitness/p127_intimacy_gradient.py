"""127 INTIMACY GRADIENT

Problem: Unless the spaces in a building are arranged in a sequence which
corresponds to their degrees of privateness, the visits made by strangers,
friends, guests, clients, family, will always be a little awkward.

Solution: Lay out the spaces of a building so that they create a sequence
which begins with the entrance and the most public parts of the building,
then leads into the somewhat more private areas, and finally to the most
private domains.

Higher patterns:
- 112 ENTRANCE TRANSITION **
- 129 COMMON AREAS AT THE HEART **
- 131 THE FLOW THROUGH ROOMS **

Lower patterns:
- 128 INDOOR SUNLIGHT **
- 130 ENTRANCE ROOM **
- 136 COUPLE'S REALM **
- 138 SLEEPING TO THE EAST **
- 141 A ROOM OF ONE'S OWN **
- 144 BATHING ROOM **
"""


class Assessor:
    """An Assessor for 127 INTIMACY GRADIENT"""

    def __init__(self, cellcomplex, circulation, shortest_path_table, **settings):
        self.settings = {
            "public_usages": {"living", "kitchen", "dining", "entrance", "hall", "foyer"},
            "private_usages": {"bedroom", "toilet", "bathroom", "study", "private"},
            "distance_scale": 8.0,
        }
        self.cellcomplex = cellcomplex
        self.circulation = circulation
        self.shortest_path_table = shortest_path_table
        for key, value in settings.items():
            self.settings[key] = value

    def execute(self, cell):
        """Score rooms where depth from entrance matches expected privacy level"""
        if cell.IsOutside():
            return 1.0
        if not self.shortest_path_table:
            return 1.0

        cell_index = cell.Get("index")
        if cell_index is None:
            return 1.0

        # Find the most accessible cell as the de-facto entrance/public zone
        min_separation = float("inf")
        entrance_index = None
        for index, paths in self.shortest_path_table.items():
            if paths:
                sep = sum(paths.values()) / len(paths)
                if sep < min_separation:
                    min_separation = sep
                    entrance_index = index

        if entrance_index is None or entrance_index == cell_index:
            return 1.0

        paths_from_entrance = self.shortest_path_table.get(entrance_index, {})
        distance = paths_from_entrance.get(cell_index)
        if distance is None:
            return 1.0

        usage = cell.Usage()
        scale = self.settings["distance_scale"]

        if usage in self.settings["private_usages"]:
            # Private rooms should be far from entrance; reward with depth
            return 0.8 + distance / scale
        if usage in self.settings["public_usages"]:
            # Public rooms should be close to entrance; reward nearness
            return 1.0 + max(0.0, 1.0 - distance / scale)
        return 1.0
