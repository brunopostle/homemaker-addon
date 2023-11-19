#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ushell as ushell


class Tests(unittest.TestCase):
    def setUp(self):
        self.shell = ushell.shell()
        self.assertEqual(len(self.shell.nodes_all()), 0)
        self.assertEqual(len(self.shell.faces_all()), 0)

        self.shell.add_facet(
            [[1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 4.0, 0.0]],
            {"normal": [0.0, 0.0, 1.0], "data": "my data"},
        )
        self.assertEqual(len(self.shell.nodes_all()), 3)
        self.assertEqual(len(self.shell.faces_all()), 1)

        self.shell.add_facet(
            [[1.0, 0.0, 0.0], [4.0, 4.0, 0.0], [0.0, 4.0, 0.0]],
            {"normal": [0.0, 0.0, 1.0], "data": "other data"},
        )
        self.assertEqual(len(self.shell.nodes_all()), 4)
        self.assertEqual(len(self.shell.faces_all()), 2)

        self.shell.add_facet(
            [[11.0, 0.0, 0.0], [14.0, 0.0, 0.0], [14.0, 4.0, 0.0]],
            {"normal": [0.0, 0.0, 1.0], "data": "some data"},
        )
        self.shell.add_facet(
            [[11.0, 0.0, 0.0], [14.0, 4.0, 0.0], [10.0, 4.0, 0.0]],
            {"normal": [0.0, 0.0, 1.0], "data": "different data"},
        )
        self.assertEqual(len(self.shell.nodes_all()), 8)
        self.assertEqual(len(self.shell.faces_all()), 4)

    def test_segment(self):
        self.shell.segment()

    def test_decompose(self):
        new_shells = self.shell.decompose()
        self.assertEqual(len(new_shells), 2)
        self.assertEqual(len(new_shells[0].nodes_all()), 4)
        self.assertEqual(len(new_shells[0].faces_all()), 2)
        self.assertEqual(len(new_shells[1].nodes_all()), 4)
        self.assertEqual(len(new_shells[1].faces_all()), 2)


if __name__ == "__main__":
    unittest.main()
