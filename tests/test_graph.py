#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from topologist import ugraph


class Tests(unittest.TestCase):
    def setUp(self):
        # two chains: A B C D E F G and H I J
        # and a cycle: K L M N

        self.graph = ugraph.graph()

        self.graph.add_edge({"C": ["D", "do"]})
        self.graph.add_edge({"D": ["E", "re"]})
        self.graph.add_edge({"F": ["G", "mi"]})
        self.graph.add_edge({"E": ["F", "fa"]})
        self.graph.add_edge({"K": ["L", "so"]})
        self.graph.add_edge({"B": ["C", "la"]})
        self.graph.add_edge({"A": ["B", "te"]})
        self.graph.add_edge({"I": ["J", "do"]})
        self.graph.add_edge({"H": ["I", "re"]})
        self.graph.add_edge({"M": ["N", "me"]})
        self.graph.add_edge({"N": ["K", "fa"]})
        self.graph.add_edge({"L": ["M", "so"]})
        self.graph.add_edge({"N": ["K", "fa"]})
        self.graph.add_edge({"L": ["M", "so"]})

    def test_starts(self):
        self.assertEqual(len(self.graph.starts()), 12)

    def test_ends(self):
        self.assertEqual(len(self.graph.ends()), 12)

    def test_sources(self):
        self.assertEqual(len(self.graph.source_vertices()), 2)

    def test_tchains(self):
        for chain in self.graph.find_chains():
            if len(chain.nodes()) == 7:
                self.assertTrue(True)
                self.assertEqual(len(chain.starts()), 6)
            elif len(chain.nodes()) == 3:
                self.assertTrue(True)
                self.assertEqual(len(chain.starts()), 2)
            else:
                self.assertTrue(False)

        cycles = self.graph.find_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0].nodes()), 4)

    def test_edge_data(self):
        self.assertEqual(self.graph.get_edge_data(["E", "F"]), "fa")
        self.assertEqual(self.graph.get_edge_data(["F", "E"]), "fa")
        self.assertFalse(self.graph.get_edge_data(["F", "A"]))


if __name__ == "__main__":
    unittest.main()
