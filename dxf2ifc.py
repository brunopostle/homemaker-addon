#!/usr/bin/python3

"""dxf2ifc - convert DXF geometry into an IFC building

This example script illustrates how to implement the homemaker-addon
functionality without any blender dependencies.

Usage:
    dxf2ifc.py mygeometry.dxf mybuilding.ifc

"""
import sys, os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from topologic import Vertex, Face, FaceUtility, CellComplex
from molior import Molior
import ezdxf
from pyinstrument import Profiler

profiler = Profiler()

# convert DXF meshes into a list of Topologic Faces
faces_ptr = []
doc = ezdxf.readfile(sys.argv[1])
model = doc.modelspace()
for entity in model:
    if entity.get_mode() == "AcDbPolyFaceMesh":
        vertices, faces = entity.indexed_faces()
        pointlist = [Vertex.ByCoordinates(*vertex.dxf.location) for vertex in vertices]

        for face in faces:
            face_stl = Face.ByVertices([pointlist[index] for index in face.indices])
            if FaceUtility.Area(face_stl) > 0.00001:
                faces_ptr.append(face_stl)

# generate a CellComplex from the Face data
cc = CellComplex.ByFaces(faces_ptr, 0.0001)

profiler.start()

# Give every Cell and Face an index number
cc.IndexTopology()
# Copy styles from Faces to the CellComplex
# cc.ApplyDictionary(faces_ptr)
# Assign Cell usages from widgets
cc.AllocateCells([])
# Generate a cirulation Graph
circulation = cc.Adjacency()
circulation.Circulation(cc)

# Traces are 2D paths that define walls, extrusions and rooms
traces, normals, elevations = cc.GetTraces()
hulls = cc.GetHulls()

molior_object = Molior(
    circulation=circulation,
    traces=traces,
    name="dxf2ifc building",
    elevations=elevations,
    hulls=hulls,
    normals=normals,
    cellcomplex=cc,
)
molior_object.execute()

profiler.stop()

molior_object.file.write(sys.argv[2])

print(profiler.output_text(unicode=True, color=True))
