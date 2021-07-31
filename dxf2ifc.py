#!/usr/bin/python3

"""dxf2ifc - convert DXF geometry into an IFC building

This example script illustrates how to implement the homemaker-addon
functionality without any blender dependencies.

Usage:
    dxf2ifc.py mygeometry.dxf mybuilding.ifc

"""
import sys, os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from topologic import Graph, Vertex, Face, FaceUtility, CellComplex
from topologist.helpers import create_stl_list
from molior import Molior
import molior.ifc
import ezdxf
from pyinstrument import Profiler

profiler = Profiler()

# convert DXF meshes into a list of Topologic Faces
faces_stl = create_stl_list(Face)
doc = ezdxf.readfile(sys.argv[1])
model = doc.modelspace()
for entity in model:
    if entity.get_mode() == "AcDbPolyFaceMesh":
        vertices, faces = entity.indexed_faces()
        pointlist = [Vertex.ByCoordinates(*vertex.dxf.location) for vertex in vertices]

        for face in faces:
            face_stl = Face.ByVertices([pointlist[index] for index in face.indices])
            if FaceUtility.Area(face_stl) > 0.00001:
                faces_stl.push_back(face_stl)

# generate a CellComplex from the Face data
cc = CellComplex.ByFaces(faces_stl, 0.0001)

profiler.start()

# Copy styles from Faces to the CellComplex
# cc.ApplyDictionary(faces_ptr)
# Assign Cell usages from widgets
cc.AllocateCells([])
# Collect unique elevations and assign storey numbers
elevations = cc.Elevations()
# Generate a cirulation Graph
circulation = Graph.Adjacency(cc)
circulation.Circulation(cc)

# generate an IFC object
ifc = molior.ifc.init("dxf2ifc building", elevations)

# Traces are 2D paths that define walls, extrusions and rooms
traces, hulls, normals = cc.GetTraces()

molior_object = Molior(
    file=ifc,
    circulation=circulation,
    elevations=elevations,
    traces=traces,
    hulls=hulls,
    normals=normals,
)
molior_object.execute()

profiler.stop()

ifc.write(sys.argv[2])

print(profiler.output_text(unicode=True, color=True))
