"""Overloads domain-specific methods onto topologic_core.Vertex"""

import topologic_core
from functools import lru_cache


@lru_cache(maxsize=1024)
def CoorAsString(self):
    """Stringify the Coordinates of this Vertex"""
    return "__".join(str(item) for item in self.Coordinates())


setattr(topologic_core.Vertex, "CoorAsString", CoorAsString)
