"""Extensions to topologic for ordinary buildings

The Topologic library and its topologic python interface models
generic non-manifold mesh 3D geometry.  This 'topologist' module
overloads additional functionality onto the topologic module that is
specific to ordinary buildings.  In particular: horizontal and vertical
faces are considered to be floors and walls; rooms are spaces with
vertical walls on all sides; non-horizontal faces form roofs and/or
soffits; and cells are tagged as inside 'rooms', voids, or outside
spaces.

With this model of what-a-building-is, it is possible to decompose the
Topologic CellComplex geometry into 'traces' and 'hulls' that define
building components.  Traces are 2D closed or open chains,
differentiated by elevation, height and style properties, typically
running in an anti-clockwise direction, these follow the outlines of
rooms, walls, eaves, string-courses etc.  Hulls are 3D open or closed
shells, differentiated by style.

Traces are defined using a simple directed-graph implementation,
'topologist.ugraph', this only supports linear chains and doesn't support
branching.  The traces contain references back to relevant Vertices,
Faces and Cells in the original Topologic CellComplex.

Hulls are defined using a simple faceted surface implementation,
'topologist.ushell'.

Topological relationships between rooms are useful for analysis of the
resulting building, this module contains methods for creating Topologic
Graph objects representing adjacency and circulation, along with methods
for referencing these back-and-forth with the original CellComplex.

This 'topologist' module knows nothing about CAD, BIM or IFC, use the
'molior' module to convert these traces into something to visualise or
solid to build.

"""

from . import topology
from . import vertex
from . import edge
from . import face
from . import cell
from . import cellcomplex
from . import graph

assert graph
