#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist import ugraph

# two chains: A B C D E F G and H I J
# and a cycle: K L M N

graph = ugraph.graph()

graph.add_edge({"C": ["D", "do"]})
graph.add_edge({"D": ["E", "re"]})
graph.add_edge({"F": ["G", "mi"]})
graph.add_edge({"E": ["F", "fa"]})
graph.add_edge({"K": ["L", "so"]})
graph.add_edge({"B": ["C", "la"]})
graph.add_edge({"A": ["B", "te"]})
graph.add_edge({"I": ["J", "do"]})
graph.add_edge({"H": ["I", "re"]})
graph.add_edge({"M": ["N", "me"]})
graph.add_edge({"N": ["K", "fa"]})
graph.add_edge({"L": ["M", "so"]})
graph.add_edge({"N": ["K", "fa"]})
graph.add_edge({"L": ["M", "so"]})


class Tests(unittest.TestCase):
    def test_starts(self):
        self.assertEqual(len(graph.starts()), 12)

    def test_ends(self):
        self.assertEqual(len(graph.ends()), 12)

    def test_sources(self):
        self.assertEqual(len(graph.source_vertices()), 2)

    def test_tchains(self):
        for chain in graph.find_chains():
            if len(chain.nodes()) == 7:
                self.assertTrue(True)
                self.assertEqual(len(chain.starts()), 6)
            elif len(chain.nodes()) == 3:
                self.assertTrue(True)
                self.assertEqual(len(chain.starts()), 2)
            else:
                self.assertTrue(False)

        cycles = graph.find_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0].nodes()), 4)

    def test_edge_data(self):
        self.assertEqual(graph.get_edge_data(["E", "F"]), "fa")
        self.assertEqual(graph.get_edge_data(["F", "E"]), "fa")
        self.assertFalse(graph.get_edge_data(["F", "A"]))


if __name__ == "__main__":
    unittest.main()
