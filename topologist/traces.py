from topologist import ugraph
from topologist.helpers import vertex_string


class Traces:
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""

    def __init__(self):
        self.traces = {}

    def add_axis(self, label, elevation, height, style, edge, face):
        """edge is two Vertices, add to graph, will split into distinct graphs later"""
        traces = self.traces
        if not label in traces:
            traces[label] = {}
        if not elevation in traces[label]:
            traces[label][elevation] = {}
        if not height in traces[label][elevation]:
            traces[label][elevation][height] = {}
        if not style in traces[label][elevation][height]:
            traces[label][elevation][height][style] = ugraph.graph()

        cells = face.CellsOrdered()
        start_coor = vertex_string(edge[0])
        end_coor = vertex_string(edge[1])

        traces[label][elevation][height][style].add_edge(
            {start_coor: [end_coor, [edge[0], edge[1], face, cells[1], cells[0]]]}
        )

    def add_axis_simple(self, label, elevation, height, style, edge, face):
        """edge is two vertices, add as a simple single edge graph"""
        cells = face.CellsOrdered()
        start_coor = vertex_string(edge[0])
        end_coor = vertex_string(edge[1])
        graph = ugraph.graph()
        graph.add_edge(
            {start_coor: [end_coor, [edge[0], edge[1], face, cells[1], cells[0]]]}
        )
        self.add_trace(label, elevation, height, style, graph)

    def add_trace(self, label, elevation, height, style, graph):
        """graph is already assembled, append"""
        traces = self.traces
        if not label in traces:
            traces[label] = {}
        if not elevation in traces[label]:
            traces[label][elevation] = {}
        if not height in traces[label][elevation]:
            traces[label][elevation][height] = {}
        if not style in traces[label][elevation][height]:
            traces[label][elevation][height][style] = []

        traces[label][elevation][height][style].append(graph)

    def process(self):
        """add_axis() leaves the trace as a single ugraph, split into a list of ugraph paths"""
        traces = self.traces
        for label in traces:
            for elevation in traces[label]:
                for height in traces[label][elevation]:
                    for style in traces[label][elevation][height]:
                        if (
                            traces[label][elevation][height][style].__class__
                            == [].__class__
                        ):
                            continue
                        graphs = traces[label][elevation][height][style].find_paths()
                        traces[label][elevation][height][style] = graphs
