"""Overloads domain-specific methods onto topologic.Vertex"""

import topologic


def CoorAsString(self):
    return "__".join(str(item) for item in self.Coordinates())


setattr(topologic.Vertex, "CoorAsString", CoorAsString)
