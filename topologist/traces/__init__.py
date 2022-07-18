import topologist.ugraph as ugraph


class Traces:
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""

    def __init__(self):
        self.traces = {}

    def add_axis(
        self,
        label,
        elevation,
        height,
        stylename,
        start_vertex=None,
        end_vertex=None,
        face=None,
        front_cell=None,
        back_cell=None,
    ):
        """add an edge defined by two vertices to graph, will split into distinct graphs later"""
        traces = self.traces
        if not label in traces:
            traces[label] = {}
        if not elevation in traces[label]:
            traces[label][elevation] = {}
        if not height in traces[label][elevation]:
            traces[label][elevation][height] = {}
        if not stylename in traces[label][elevation][height]:
            traces[label][elevation][height][stylename] = ugraph.graph()

        traces[label][elevation][height][stylename].add_edge(
            {
                start_vertex.CoorAsString(): [
                    end_vertex.CoorAsString(),
                    {
                        "start_vertex": start_vertex,
                        "end_vertex": end_vertex,
                        "face": face,
                        "back_cell": back_cell,
                        "front_cell": front_cell,
                    },
                ]
            }
        )

    def add_axis_simple(
        self,
        label,
        elevation,
        height,
        stylename,
        start_vertex=None,
        end_vertex=None,
        face=None,
        front_cell=None,
        back_cell=None,
    ):
        """append a graph consisting of a single edge defined by two vertices"""
        graph = ugraph.graph()
        graph.add_edge(
            {
                start_vertex.CoorAsString(): [
                    end_vertex.CoorAsString(),
                    {
                        "start_vertex": start_vertex,
                        "end_vertex": end_vertex,
                        "face": face,
                        "back_cell": back_cell,
                        "front_cell": front_cell,
                    },
                ]
            }
        )
        self.add_trace(label, elevation, height, stylename, graph=graph)

    def add_trace(self, label, elevation, height, stylename, graph=ugraph.graph()):
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
                        if type(traces[label][elevation][height][stylename]) == list:
                            continue
                        graphs = traces[label][elevation][height][
                            stylename
                        ].find_paths()
                        traces[label][elevation][height][stylename] = graphs
