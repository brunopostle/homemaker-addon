#!/usr/bin/python3

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from topologic_core import Vertex, StringAttribute
import topologist.vertex

assert topologist.vertex


def test_dictionary(monkeypatch):
    """Test dictionary operations"""
    my_vertex = Vertex.ByCoordinates(0, 0, 0)
    my_key = "message"
    my_value = StringAttribute("Hello World")

    # Copy a Dictionary (if any) from my_vertex
    my_dictionary = my_vertex.GetDictionary()
    # add some stuff
    my_dictionary.Add(my_key, my_value)
    # re-add a copy of this dictionary to my_vertex
    my_vertex.SetDictionary(my_dictionary)

    # fetch a copy of my_vertex dictionary
    retrieved_dictionary = my_vertex.GetDictionary()
    # add some more stuff
    other_key = "usage"
    other_value = StringAttribute("Kitchen")
    retrieved_dictionary.Add(other_key, other_value)
    # add a copy of this amended dictionary to my_vertex
    my_vertex.SetDictionary(retrieved_dictionary)

    # Retrieve Dictionary
    dictionary = my_vertex.GetDictionary()
    value = dictionary.ValueAtKey(my_key)

    # Bind Retrieved String Value and Print It
    string_struct = value.StringValue()
    assert str(string_struct) == "Hello World"

    retrieved_value = dictionary.ValueAtKey(other_key)
    retrieved_string_struct = retrieved_value.StringValue()
    assert str(retrieved_string_struct) == "Kitchen"


def test_get_set():
    """Test get and set methods on topology"""
    topology = Vertex.ByCoordinates(1, 1, 0)
    assert topology.Get("what") is None
    topology.Set("message", "This is an oldy")
    topology.Set("message", "This is a string")
    assert topology.Get("message") == "This is a string"
    topology.Set("usage", "Bedroom")
    assert topology.Get("usage") == "Bedroom"
    assert topology.Get("message") == "This is a string"
    assert topology.Get("what") is None
