#!/usr/bin/python3

import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cppyy
from cppyy.gbl.std import string
from topologic import Vertex, StringAttribute
import topologist

my_vertex = Vertex.ByCoordinates(0,0,0)
my_key = string("message")
my_value = StringAttribute('Hello World')

# Copy a Dictionary (if any) from my_vertex
my_dictionary = my_vertex.GetDictionary()
# add some stuff
my_dictionary.Add(my_key, my_value)
# re-add a copy of this dictionary to my_vertex
my_vertex.SetDictionary(my_dictionary)

# fetch a copy of my_vertex dictionary
retrieved_dictionary = my_vertex.GetDictionary()
# add some more stuff
other_key = string("usage")
other_value = StringAttribute('Kitchen')
retrieved_dictionary.Add(other_key, other_value)
# add a copy of this amended dictionary to my_vertex
my_vertex.SetDictionary(retrieved_dictionary)

class Tests(unittest.TestCase):
    def test_dictionary(self):
        """read"""
        # Retrieve Dictionary
        dictionary = my_vertex.GetDictionary()
        value = dictionary.ValueAtKey(my_key)

        # Bind Retrieved String Value and Print It
        string_struct = cppyy.bind_object(value.Value(), 'StringStruct')
        self.assertEqual(string_struct.getString, "Hello World")

        retrieved_value = dictionary.ValueAtKey(other_key)
        retrieved_string_struct = cppyy.bind_object(retrieved_value.Value(), 'StringStruct')
        self.assertEqual(retrieved_string_struct.getString, "Kitchen")

    def test_get_set(self):
        topology = Vertex.ByCoordinates(1,1,0)
        self.assertEqual(topology.Get('what'), None)
        topology.Set('message', 'This is an oldy')
        topology.Set('message', 'This is a string')
        self.assertEqual(topology.Get('message'), 'This is a string')
        topology.Set('usage', 'Bedroom')
        self.assertEqual(topology.Get('usage'), 'Bedroom')
        self.assertEqual(topology.Get('message'), 'This is a string')
        self.assertEqual(topology.Get('what'), None)

if __name__ == '__main__':
    unittest.main()
