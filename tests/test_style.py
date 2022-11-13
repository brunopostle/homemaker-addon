#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.style import Style


class Tests(unittest.TestCase):
    """Style"""

    def test_init(self):
        mystyle = Style()
        self.assertTrue("default" in mystyle.data)
        self.assertEqual(len(mystyle.data["default"]["ancestors"]), 0)
        self.assertTrue("courtyard" in mystyle.data)
        self.assertEqual(len(mystyle.data["courtyard"]["ancestors"]), 1)
        self.assertTrue("fancy" in mystyle.data)

        fancy = mystyle.get("fancy")
        self.assertTrue("traces" in fancy)
        default = mystyle.get("default")
        mystyle.get("courtyard")
        default2 = mystyle.get("nonsuch")
        self.assertEqual(default, default2)


if __name__ == "__main__":
    unittest.main()
