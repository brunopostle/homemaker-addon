#!/usr/bin/python3

"""brep2ifc - convert BREP geometry into an IFC building

This example script illustrates how to implement the homemaker-addon
functionality without any blender dependencies.

Usage:
    brep2ifc.py mygeometry.brep mybuilding.ifc

"""
import sys, os, datetime

sys.path.append("/home/bruno/src/homemaker-addon")
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from topologic import Graph, Topology, Vertex, Face, CellComplex, TopologyUtility
from topologist.helpers import create_stl_list
from molior import Molior
import molior.ifc

print("Start", datetime.datetime.now())
brep_file = open(sys.argv[1], "r")
topology = Topology.ByString(brep_file.read())
print("BREP imported", datetime.datetime.now())

origin = Vertex.ByCoordinates(0.0, 0.0, 0.0)
# topology_scaled = TopologyUtility.Scale(topology, origin, 0.3048, 0.3048, 0.3048)
# print("BREP scale from feet to metres", datetime.datetime.now())
topology_scaled = TopologyUtility.Scale(topology, origin, 1.0, 1.0, 1.0)

faces_stl = create_stl_list(Face)
topology_scaled.Faces(faces_stl)
print(str(len(faces_stl)), "faces", datetime.datetime.now())

cc = CellComplex.ByFaces(faces_stl, 0.0001)
print("CellComplex created", datetime.datetime.now())

# Copy styles from Faces to the CellComplex
# cc.ApplyDictionary(faces_ptr)
# Assign Cell usages from widgets
cc.AllocateCells([])
# Collect unique elevations and assign storey numbers
elevations = cc.Elevations()
print(str(len(elevations)), "Elevations", datetime.datetime.now())
# Generate a cirulation Graph
circulation = Graph.Adjacency(cc)
circulation.Circulation(cc)
print("Circulation Graph generated", datetime.datetime.now())

# generate an IFC object
ifc = molior.ifc.init("brep2ifc building", elevations)

# Traces are 2D paths that define walls, extrusions and rooms
traces, hulls = cc.GetTraces()
print("Traces calculated", datetime.datetime.now())

molior_object = Molior()
molior_object.Process(ifc, circulation, elevations, traces)
print("IFC model created", datetime.datetime.now())

ifc.write(sys.argv[2])
