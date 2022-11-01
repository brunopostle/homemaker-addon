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

        # currently highparapet.dxf only exists in courtyard style
        self.assertFalse(mystyle.get_file("default", "highparapet.dxf"))
        self.assertFalse(mystyle.get_file("fancy", "highparapet.dxf"))
        self.assertTrue(mystyle.get_file("courtyard", "highparapet.dxf"))
        # newel-bottom.dxf is in the default style so any style gets it
        self.assertTrue(mystyle.get_file("default", "newel-bottom.dxf"))
        self.assertTrue(mystyle.get_file("courtyard", "newel-bottom.dxf"))
        self.assertTrue(mystyle.get_file("fancy", "newel-bottom.dxf"))
        # newel-bottom.dxf isn't in fancy, so result is same as default
        self.assertEqual(
            mystyle.get_file("fancy", "newel-bottom.dxf"),
            mystyle.get_file("default", "newel-bottom.dxf"),
        )
        # nonsuch style doesn't exist, so result is same as default
        self.assertEqual(
            mystyle.get_file("nonsuch", "newel-bottom.dxf"),
            mystyle.get_file("default", "newel-bottom.dxf"),
        )


if __name__ == "__main__":
    unittest.main()
