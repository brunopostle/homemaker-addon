"""Extensions to topologicPy for ordinary buildings

The Topologic library and its topologicPy python interface models
generic non-manifold mesh 3D geometry.  This 'topologist' module
overloads additional functionality onto the topologicPy module that is
specific to ordinary buildings.  In particular: horizontal and vertical
faces are considered to be floors and walls; rooms are spaces with
vertical walls on all sides; non-horizontal faces form roofs and/or
soffits; and cells are tagged as indoor 'rooms', or outdoor spaces.

With this model of what-a-building-is, it is possible to decompose the
Topologic CellComplex geometry into 'traces' that define building
components.  Traces are 2D closed or open chains, differentiated by
elevation, height and style properties, typically running in an
anti-clockwise direction, these follow the outlines of rooms, walls,
eaves, string-courses etc.

Traces are defined using a simple directed-graph implementation, called
'ugraph', this only supports linear chains and doesn't support
branching.  The traces contain references back to relevant Vertices,
Faces and Cells in the original Topologic CellComplex.

Topological relationships between rooms are useful for analysis of the
resulting building, this module contains methods for creating Topologic
Graph objects representing adjaceny and circulation, along with methods
for referencing these back-and-forth with the original CellComplex.

"""

from . import topology
from . import edge
from . import face
from . import cell
from . import cellcomplex
from . import graph
