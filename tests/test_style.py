#!/usr/bin/python3

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.style import Style


def test_style_initialization():
    """Test the Style class initialization and basic properties"""
    mystyle = Style()

    # Check default style
    assert "default" in mystyle.data
    assert len(mystyle.data["default"]["ancestors"]) == 0

    # Check courtyard style
    assert "courtyard" in mystyle.data
    assert len(mystyle.data["courtyard"]["ancestors"]) == 1

    # Check fancy style
    assert "fancy" in mystyle.data

    # Test get method
    fancy = mystyle.get("fancy")
    assert "traces" in fancy

    default = mystyle.get("default")
    mystyle.get("courtyard")  # Ensure this doesn't raise an exception

    # Test fallback to default when style not found
    default2 = mystyle.get("nonsuch")
    assert default == default2
