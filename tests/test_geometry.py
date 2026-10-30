import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.geometry import point_on_segment


def test_point_on_segment():
    start = [0.0, 0.0, 3.0]
    end = [4.0, 0.0, 3.0]
    assert point_on_segment([2.0, 0.0, 3.0], start, end)
    assert point_on_segment(start, start, end)
    assert point_on_segment(end, start, end)
    assert not point_on_segment([2.0, 0.1, 3.0], start, end)
    assert not point_on_segment([2.0, 0.0, 3.1], start, end)
    # beyond the ends, on the same line
    assert not point_on_segment([4.1, 0.0, 3.0], start, end)
    assert not point_on_segment([-0.1, 0.0, 3.0], start, end)
