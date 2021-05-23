#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph


class Tests(unittest.TestCase):
    def setUp(self):
        self.graph = ugraph.graph()

        self.graph.graph = {
            "1.4466087818145752__3.225928783416748__0.0": [
                "2.756314754486084__-2.088371753692627__0.0",
                None,
            ],
            "6.636378288269043__4.081480979919434__0.0": [
                "1.4466087818145752__3.225928783416748__0.0",
                None,
            ],
            "8.317962646484375__-2.2967023849487305__0.0": [
                "6.636378288269043__4.081480979919434__0.0",
                None,
            ],
            "3.0601770877838135__-3.321331262588501__0.0": [
                "8.317962646484375__-2.2967023849487305__0.0",
                None,
            ],
            "2.756314754486084__-2.088371753692627__0.0": [
                "3.0601770877838135__-3.321331262588501__0.0",
                None,
            ],
        }

    def test_cycle(self):
        self.assertFalse(self.graph.is_simple_cycle())
        paths = self.graph.find_paths()
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].is_simple_cycle())

    def test_starts(self):
        self.assertEqual(len(self.graph.starts()), 5)
        self.assertEqual(len(self.graph.ends()), 5)


if __name__ == "__main__":
    unittest.main()
