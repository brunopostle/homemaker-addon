#!/usr/bin/python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.style import style


class Tests(unittest.TestCase):
    """Style"""

    def test_init(self):
        mystyle = style()
        # print(mystyle.data)


if __name__ == "__main__":
    unittest.main()
