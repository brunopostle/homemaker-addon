class graph:
    """A simple directed graph that only supports linear chains and loops"""

    # Note, ideally this would be represented by a Topologic Wire.  But
    # Wires don't support single-edge Wires, or arbitrary dictionary
    # references to python objects such as Topologic Cells and Faces in
    # the CellComplex

    def __init__(self):
        self.graph = {}

    def add_edge(self, edge):
        """graph.add_edge({'C': ['D', 'do']})"""
        for key in edge:
            self.graph[key] = edge[key]

    # FIXME doesn't appear to be in use
    def get_edge_data(self, edge):
        if edge[0] in self.graph and self.graph[edge[0]][0] == edge[1]:
            return self.graph[edge[0]][1]
        if edge[1] in self.graph and self.graph[edge[1]][0] == edge[0]:
            return self.graph[edge[1]][1]
        return None

    def nodes(self):
        """Return nodes in use"""
        result = set()
        for vertex in self.graph:
            if self.graph[vertex]:
                result.add(vertex)
                result.add(self.graph[vertex][0])
        return result

    def edges(self):
        """Return edges as a list of node pairs"""
        return [
            [vertex, self.graph[vertex][0]]
            for vertex in self.graph
            if self.graph[vertex]
        ]

    def starts(self):
        """Return a list of starting nodes"""
        return [vertex for vertex in self.graph if self.graph[vertex]]

    def ends(self):
        """Return a list of ending nodes"""
        return [self.graph[vertex][0] for vertex in self.graph if self.graph[vertex]]

    def is_simple_cycle(self):
        """Does the last node connect to the first node?"""
        if len(self.graph) > 0 and self.starts()[0] == self.ends()[-1]:
            return True
        return False

    def source_vertices(self):
        """Return a list of starting nodes that are not ends"""
        start_set = set(self.starts())
        end_set = set(self.ends())
        return start_set - end_set

    def find_chains(self):
        """Return a list of open chains as new graph objects.
        Results are removed from this graph"""
        result = []
        for vertex in self.source_vertices():
            chain = graph()
            todo = True
            while todo is True:
                chain.add_edge({vertex: self.graph[vertex]})
                if self.graph[vertex] and self.graph[vertex][0] in self.graph:
                    vertex_next = self.graph[vertex][0]
                    self.graph[vertex] = False
                    vertex = vertex_next
                else:
                    self.graph[vertex] = False
                    todo = False
            result.append(chain)
        return result

    def find_cycles(self):
        """Return a list of closed cycles as new graph objects.
        Results are removed from this graph. This method assumes
        that find_chains() has already been run"""
        result = []
        visited = set()

        for vertex in list(self.graph.keys()):
            if vertex in visited or not self.graph[vertex]:
                continue

            cycle = graph()
            current = vertex
            cycle_nodes = set()

            while self.graph[current]:
                cycle.add_edge({current: self.graph[current]})
                visited.add(current)

                next_vertex = self.graph[current][0]
                self.graph[current] = False

                if next_vertex in cycle_nodes:
                    # We've found a cycle
                    break

                cycle_nodes.add(next_vertex)
                current = next_vertex

                if current not in self.graph or not self.graph[current]:
                    break

            result.append(cycle)

        return result

    def find_paths(self):
        """Return result of find_chains() and find_cycles() as a single list"""
        return self.find_chains() + self.find_cycles()
