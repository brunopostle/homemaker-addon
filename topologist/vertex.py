"""Overloads domain-specific methods onto topologic.Vertex"""

import topologic


def String(self):
    return str(self.X()) + "__" + str(self.Y()) + "__" + str(self.Z())


setattr(topologic.Vertex, "String", String)
