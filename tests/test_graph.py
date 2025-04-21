#!/usr/bin/python3

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph


@pytest.fixture
def graph():
    """Fixture to create and return a graph for testing"""
    graph_instance = ugraph.graph()

    graph_instance.add_edge({"C": ["D", "do"]})
    graph_instance.add_edge({"D": ["E", "re"]})
    graph_instance.add_edge({"F": ["G", "mi"]})
    graph_instance.add_edge({"E": ["F", "fa"]})
    graph_instance.add_edge({"K": ["L", "so"]})
    graph_instance.add_edge({"B": ["C", "la"]})
    graph_instance.add_edge({"A": ["B", "te"]})
    graph_instance.add_edge({"I": ["J", "do"]})
    graph_instance.add_edge({"H": ["I", "re"]})
    graph_instance.add_edge({"M": ["N", "me"]})
    graph_instance.add_edge({"N": ["K", "fa"]})
    graph_instance.add_edge({"L": ["M", "so"]})
    graph_instance.add_edge({"N": ["K", "fa"]})
    graph_instance.add_edge({"L": ["M", "so"]})

    return graph_instance


def test_starts(graph):
    """Test the number of starts in the graph"""
    assert len(graph.starts()) == 12


def test_ends(graph):
    """Test the number of ends in the graph"""
    assert len(graph.ends()) == 12


def test_sources(graph):
    """Test the number of source vertices"""
    assert len(graph.source_vertices()) == 2


def test_tchains(graph):
    """Test graph chains and cycles"""
    chains = list(graph.find_chains())

    # Check chain lengths and starts
    for chain in chains:
        if len(chain.nodes()) == 7:
            assert len(chain.starts()) == 6
        elif len(chain.nodes()) == 3:
            assert len(chain.starts()) == 2
        else:
            assert False, f"Unexpected chain length: {len(chain.nodes())}"

    # Check cycles
    cycles = graph.find_cycles()
    assert len(cycles) == 1
    assert len(cycles[0].nodes()) == 4


def test_edge_data(graph):
    """Test edge data retrieval"""
    assert graph.get_edge_data(["E", "F"]) == "fa"
    assert graph.get_edge_data(["F", "E"]) == "fa"
    assert not graph.get_edge_data(["F", "A"])
