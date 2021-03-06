""" Traces are 2D closed or open chains that define building elements,
differentiated by elevation, height and style properties.  Typically
running in an anti-clockwise direction, these follow the outlines of
rooms, walls, eaves, string-courses etc.

There are traces for each space/room usage:

* kitchen
* living
* bedroom
* toilet
* sahn (an outdoor circulation space)
* circulation
* stair
* retail
* outside
* void (an internal space that doesn't qualify as a room)

There are traces for each wall condition:

* external
* internal (these are always a single segment long)
* open (an external 'wall' to outdoor space)

There are traces that follow the top and bottom horizontal edges of
external walls:

* top-vertical-up (a string course between two vertical walls)
* top-forward-up
* top-forward-level (a horizontal soffit at the top of a wall)
* top-forward-down
* top-backward-up (a typical eave with a pitched roof above)
* top-backward-level (a typical eave with a horizontal roof behind)
* top-backward-down (a typical eave at the top of a monopitch roof)
* bottom-vertical-down (a string course between two vertical walls)
* bottom-forward-up (a box gutter where a pitched roof meets a wall)
* bottom-forward-level (a wall on a flat roof)
* bottom-forward-down (a wall above a lean-to pitched roof)
* bottom-backward-up
* bottom-backward-level (a horizontal soffit behind a wall)
* bottom-backward-down

And a trace that follows the bottom of internal walls with nothing
below:

* internal-unsupported (always one segment long)

"""

import topologist.ugraph as ugraph


class Traces:
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""

    def __init__(self):
        self.traces = {}

    def add_axis(self, label, elevation, height, stylename, edge, face):
        """edge is two Vertices, add to graph, will split into distinct graphs later"""
        traces = self.traces
        if not label in traces:
            traces[label] = {}
        if not elevation in traces[label]:
            traces[label][elevation] = {}
        if not height in traces[label][elevation]:
            traces[label][elevation][height] = {}
        if not stylename in traces[label][elevation][height]:
            traces[label][elevation][height][stylename] = ugraph.graph()

        cells = face.CellsOrdered()
        start_coor = edge[0].CoorAsString()
        end_coor = edge[1].CoorAsString()

        traces[label][elevation][height][stylename].add_edge(
            {start_coor: [end_coor, [edge[0], edge[1], face, cells[1], cells[0]]]}
        )

    def add_axis_simple(self, label, elevation, height, stylename, edge, face):
        """edge is two vertices, add as a simple single edge graph"""
        cells = face.CellsOrdered()
        start_coor = edge[0].CoorAsString()
        end_coor = edge[1].CoorAsString()
        graph = ugraph.graph()
        graph.add_edge(
            {start_coor: [end_coor, [edge[0], edge[1], face, cells[1], cells[0]]]}
        )
        self.add_trace(label, elevation, height, stylename, graph)

    def add_trace(self, label, elevation, height, stylename, graph):
        """graph is already assembled, append"""
        traces = self.traces
        if not label in traces:
            traces[label] = {}
        if not elevation in traces[label]:
            traces[label][elevation] = {}
        if not height in traces[label][elevation]:
            traces[label][elevation][height] = {}
        if not stylename in traces[label][elevation][height]:
            traces[label][elevation][height][stylename] = []

        traces[label][elevation][height][stylename].append(graph)

    def process(self):
        """add_axis() leaves the trace as a single ugraph, split into a list of ugraph paths"""
        traces = self.traces
        for label in traces:
            for elevation in traces[label]:
                for height in traces[label][elevation]:
                    for stylename in traces[label][elevation][height]:
                        if (
                            traces[label][elevation][height][stylename].__class__
                            == [].__class__
                        ):
                            continue
                        graphs = traces[label][elevation][height][
                            stylename
                        ].find_paths()
                        traces[label][elevation][height][stylename] = graphs
