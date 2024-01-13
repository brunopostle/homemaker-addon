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
        if self.graph[edge[0]] and self.graph[edge[0]][0] == edge[1]:
            return self.graph[edge[0]][1]
        if self.graph[edge[1]] and self.graph[edge[1]][0] == edge[0]:
            return self.graph[edge[1]][1]
        return None

    def nodes(self):
        """Return node in use"""
        result = {}
        for vertex in self.graph:
            result[vertex] = True
            result[self.graph[vertex][0]] = True
        return result

    def edges(self):
        """Return edges as a list of node pairs"""
        return [[vertex, self.graph[vertex][0]] for vertex in self.graph]

    def starts(self):
        """Return a list of starting nodes"""
        return [vertex_a for vertex_a in self.graph]

    def ends(self):
        """Return a list of ending nodes"""
        return [self.graph[vertex_a][0] for vertex_a in self.graph]

    def is_simple_cycle(self):
        """Does the last node connect to the first node?"""
        if len(self.graph) > 0 and self.starts()[0] == self.ends()[-1]:
            return True
        return False

    def source_vertices(self):
        """Return a list of starting nodes that are not ends"""
        result = []
        start_list = self.starts()
        end_list = self.ends()
        for start in start_list:
            if start not in end_list:
                result.append(start)
        return result

    def find_chains(self):
        """Return a list of open chains as new graph objects.
        Results are removed from this graph"""
        result = []
        source_list = self.source_vertices()
        for vertex in source_list:
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
        for vertex in self.graph:
            if not self.graph[vertex]:
                continue
            cycle = graph()
            todo = True
            while todo is True:
                if self.graph[vertex] and self.graph[vertex][0] in self.graph:
                    cycle.add_edge({vertex: self.graph[vertex]})
                    vertex_next = self.graph[vertex][0]
                    self.graph[vertex] = False
                    vertex = vertex_next
                else:
                    self.graph[vertex] = False
                    todo = False
            result.append(cycle)
        return result

    def find_paths(self):
        """Return result of find_chains() and find_cycles() as a single list"""
        return self.find_chains() + self.find_cycles()
