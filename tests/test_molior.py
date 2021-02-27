#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from molior import Wall, Ceiling

class Tests(unittest.TestCase):
    """Wall subclasses Molior"""
    def test_wall(self):
        wall = Wall()

        self.assertEqual(wall.height, 0.0)
        wall.height = 3.0
        self.assertEqual(wall.height, 3.0)

        self.assertEqual(wall.outer, 0.25)
        wall.outer = 0.3
        self.assertEqual(wall.outer, 0.3)

        wall2 = Wall({'height': 2.7, 'outer': 0.4})
        self.assertEqual(wall2.height, 2.7)
        self.assertEqual(wall2.outer, 0.4)

        wall3 = Wall({'closed': False, 'path': [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]]})
        self.assertEqual(len(wall3.path), 3)
        self.assertEqual(len(wall3.openings), 2)

        wall4 = Wall({'closed': True, 'path': [[0.0, 0.0], [5.0, 0.0], [10.0, 5.0]]})
        self.assertEqual(len(wall4.path), 3)
        self.assertEqual(len(wall4.openings), 3)
        self.assertEqual(wall4.path[2], [10.0, 5.0])

        wall4.populate_exterior_openings(2, 'kitchen', 0)
        self.assertEqual(wall4.openings[2][0], {'name': 'kitchen outside window', 'along': 0.5, 'size': 0})

        self.assertEqual(wall4.__dict__['guid'], 'my building')

    def test_ceiling(self):
        ceiling = Ceiling()
        self.assertEqual(ceiling.type, 'molior-ceiling')

if __name__ == '__main__':
    unittest.main()
