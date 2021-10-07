"""Overloads domain-specific methods onto topologic.Vertex"""

import topologic


def CoorAsString(self):
    return "__".join(str(item) for item in list(self.Coordinates()))


setattr(topologic.Vertex, "CoorAsString", CoorAsString)
