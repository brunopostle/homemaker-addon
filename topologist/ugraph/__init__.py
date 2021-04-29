class graph:
    """A simple directed graph that only supports linear chains and loops"""

    def __init__(self):
        self.graph = {}

    def add_edge(self, edge):
        """graph.add_edge({'C': ['D', 'do']})"""
        for key in edge:
            self.graph[key] = edge[key]

    def get_edge_data(self, edge):
        if self.graph[edge[0]] and self.graph[edge[0]][0] == edge[1]:
            return self.graph[edge[0]][1]
        if self.graph[edge[1]] and self.graph[edge[1]][0] == edge[0]:
            return self.graph[edge[1]][1]
        return None

    def nodes(self):
        result = {}
        for vertex in self.graph:
            result[vertex] = True
            result[self.graph[vertex][0]] = True
        return result

    def edges(self):
        return [[vertex, self.graph[vertex][0]] for vertex in self.graph]

    def starts(self):
        return [vertex_a for vertex_a in self.graph]

    def ends(self):
        return [self.graph[vertex_a][0] for vertex_a in self.graph]

    def is_simple_cycle(self):
        """does the last node connect to the first node?"""
        if len(self.graph) > 0 and self.starts()[0] == self.ends()[-1]:
            return True
        return False

    def source_vertices(self):
        result = []
        start_list = self.starts()
        end_list = self.ends()
        for start in start_list:
            if not start in end_list:
                result.append(start)
        return result

    def find_chains(self):
        """find_chains() and find_cycles() destroy the graph"""
        result = []
        source_list = self.source_vertices()
        for vertex in source_list:
            chain = graph()
            todo = True
            while todo == True:
                chain.add_edge({vertex: self.graph[vertex]})
                if self.graph[vertex][0] in self.graph:
                    vertex_next = self.graph[vertex][0]
                    self.graph[vertex] = False
                    vertex = vertex_next
                else:
                    self.graph[vertex] = False
                    todo = False
            result.append(chain)
        return result

    def find_cycles(self):
        """find_cycles() destroys the graph and needs to be run after find_chains()"""
        result = []
        for vertex in self.graph:
            if not self.graph[vertex]:
                continue
            cycle = graph()
            todo = True
            while todo == True:
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
        """return result of find_chains() and find_cycles() as a single list"""
        return self.find_chains() + self.find_cycles()
