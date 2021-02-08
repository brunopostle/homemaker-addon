#!/usr/bin/python3

import unittest

class evil_graph:
    def __init__(self):
        self.graph = {}

    def add_edge(self, edge):
        for key in edge:
            self.graph[key] = edge[key]

    def starts(self):
        result = []
        for vertex_a in self.graph:
            result.append(vertex_a)
        return result

    def ends(self):
        result = []
        for vertex_a in self.graph:
            result.append(self.graph[vertex_a][0])
        return result

    def source_vertices(self):
        result = []
        start_list = self.starts()
        end_list = self.ends()
        for start in start_list:
            if not start in end_list:
                result.append(start)
        return result

    def find_chains(self):
        result = []
        source_list = self.source_vertices()
        for vertex in source_list:
            chain = []
            todo = True
            while todo == True:
                chain.append({vertex: self.graph[vertex]})
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
        result = []
        for vertex in self.graph:
            if not self.graph[vertex]:
                continue
            cycle = []
            todo = True
            while todo == True:
                if self.graph[vertex] and self.graph[vertex][0] in self.graph:
                    cycle.append({vertex: self.graph[vertex]})
                    vertex_next = self.graph[vertex][0]
                    self.graph[vertex] = False
                    vertex = vertex_next
                else:
                    self.graph[vertex] = False
                    todo = False
            result.append(cycle)
        return result

class Tests(unittest.TestCase):
    def test_starts(self):
        self.assertEqual(len(graph.starts()), 12)

    def test_ends(self):
        self.assertEqual(len(graph.ends()), 12)

    def test_sources(self):
        self.assertEqual(len(graph.source_vertices()), 2)

    def test_tchains(self):
        for chain in graph.find_chains():
            if len(chain) == 6:
                self.assertTrue(True)
            elif len(chain) == 2:
                self.assertTrue(True)
            else:
                self.assertTrue(False)

        cycles = graph.find_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0]), 4)

# two chains: A B C D E F G and H I J
# and a cycle: K L M N

graph = evil_graph()

graph.add_edge({'C': ['D', 'do']})
graph.add_edge({'D': ['E', 're']})
graph.add_edge({'F': ['G', 'mi']})
graph.add_edge({'E': ['F', 'fa']})
graph.add_edge({'K': ['L', 'so']})
graph.add_edge({'B': ['C', 'la']})
graph.add_edge({'A': ['B', 'te']})
graph.add_edge({'I': ['J', 'do']})
graph.add_edge({'H': ['I', 're']})
graph.add_edge({'M': ['N', 'me']})
graph.add_edge({'N': ['K', 'fa']})
graph.add_edge({'L': ['M', 'so']})
graph.add_edge({'N': ['K', 'fa']}) 
graph.add_edge({'L': ['M', 'so']})

if __name__ == '__main__':
    unittest.main()
