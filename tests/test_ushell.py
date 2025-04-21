#!/usr/bin/python3

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ushell as ushell


def test_shell_initial_state():
    shell = ushell.shell()
    assert len(shell.nodes_all()) == 0
    assert len(shell.faces_all()) == 0


def test_shell_add_facets():
    shell = ushell.shell()

    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "my data"},
    )
    assert len(shell.nodes_all()) == 3
    assert len(shell.faces_all()) == 1

    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 4.0, 0.0], [0.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "other data"},
    )
    assert len(shell.nodes_all()) == 4
    assert len(shell.faces_all()) == 2

    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 0.0, 0.0], [14.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "some data"},
    )
    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 4.0, 0.0], [10.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "different data"},
    )
    assert len(shell.nodes_all()) == 8
    assert len(shell.faces_all()) == 4


def test_shell_segment():
    shell = ushell.shell()

    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "my data"},
    )
    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 4.0, 0.0], [0.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "other data"},
    )
    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 0.0, 0.0], [14.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "some data"},
    )
    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 4.0, 0.0], [10.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "different data"},
    )

    shell.segment()


def test_shell_decompose():
    shell = ushell.shell()

    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "my data"},
    )
    shell.add_facet(
        [[1.0, 0.0, 0.0], [4.0, 4.0, 0.0], [0.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "other data"},
    )
    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 0.0, 0.0], [14.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "some data"},
    )
    shell.add_facet(
        [[11.0, 0.0, 0.0], [14.0, 4.0, 0.0], [10.0, 4.0, 0.0]],
        {"normal": [0.0, 0.0, 1.0], "data": "different data"},
    )

    new_shells = shell.decompose()
    assert len(new_shells) == 2
    assert len(new_shells[0].nodes_all()) == 4
    assert len(new_shells[0].faces_all()) == 2
    assert len(new_shells[1].nodes_all()) == 4
    assert len(new_shells[1].faces_all()) == 2
