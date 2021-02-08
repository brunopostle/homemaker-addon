#!/usr/bin/python3

import os
import sys
import unittest

import networkx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import nx_acycles

nxgraph = networkx.DiGraph()

# two chains: A B C D E F G and H I J
# and a cycle: K L M N

nxgraph.add_edges_from([('C', 'D'), ('D', 'E'), ('F', 'G'), ('E', 'F'), ('K', 'L'),
                        ('B', 'C'), ('A', 'B'), ('I', 'J'), ('H', 'I'), ('M', 'N'),
                        ('N', 'K'), ('L', 'M')])

class Tests(unittest.TestCase):
    def test_acyclic(self):
        acycles = nx_acycles(nxgraph)
        self.assertEqual(len(acycles), 2)
        self.assertEqual(len(acycles[0]), 7)
        self.assertEqual(len(acycles[1]), 3)

    def test_cycles(self):
        cycles = networkx.simple_cycles(nxgraph)
        list_cycles = list(cycles)
        self.assertEqual(len(list_cycles), 1)
        self.assertEqual(len(list_cycles[0]), 4)

    def test_edges(self):
        F_G = False
        N_K = False
        for edge in nxgraph.edges:
            if (edge[0] == 'F' and edge[1] == 'G'):
                F_G = True
            if (edge[0] == 'N' and edge[1] == 'K'):
                N_K = True
        self.assertTrue(F_G)
        self.assertTrue(N_K)

if __name__ == '__main__':
    unittest.main()
