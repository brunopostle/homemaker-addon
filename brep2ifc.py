#!/usr/bin/python3

"""brep2ifc - convert BREP geometry into an IFC building

This example script illustrates how to implement the homemaker-addon
functionality without any blender dependencies.

Usage:
    brep2ifc.py mygeometry.brep mybuilding.ifc

"""
import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from topologic import Topology, Vertex, TopologyUtility
from molior import Molior

print("Start", datetime.datetime.now())
brep_file = open(sys.argv[1], "r")
topology = Topology.ByString(brep_file.read())
print("BREP imported", datetime.datetime.now())

origin = Vertex.ByCoordinates(0.0, 0.0, 0.0)
# topology_scaled = TopologyUtility.Scale(topology, origin, 0.3048, 0.3048, 0.3048)
# print("BREP scale from feet to meters", datetime.datetime.now())
topology_scaled = TopologyUtility.Scale(topology, origin, 1.0, 1.0, 1.0)

faces_ptr = []
topology_scaled.Faces(faces_ptr)

print(str(len(faces_ptr)), "faces", datetime.datetime.now())

molior_object = Molior.from_faces_and_widgets(faces=faces_ptr, name="brep2ifc building")
molior_object.execute()

print("IFC model created", datetime.datetime.now())

molior_object.file.write(sys.argv[2])
