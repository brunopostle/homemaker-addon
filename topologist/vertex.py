"""Overloads domain-specific methods onto topologic.Vertex"""

import topologic


def CoorAsString(self):
    return str(self.X()) + "__" + str(self.Y()) + "__" + str(self.Z())


setattr(topologic.Vertex, "CoorAsString", CoorAsString)
