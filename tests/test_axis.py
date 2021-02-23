#!/usr/bin/python3

import os
import sys
import unittest

from topologic import Vertex, Edge, Wire, Face, CellComplex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from topologist.helpers import create_stl_list

points = [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 10.0, 0.0], [0.0, 10.0, 0.0],
          [0.0, 0.0, 10.0], [10.0, 0.0, 10.0], [10.0, 10.0, 10.0], [0.0, 10.0, 10.0]]

vertices = []
for point in points:
    vertex = Vertex.ByCoordinates(point[0], point[1], point[2])
    vertices.append(vertex)

# faces have mixed normals
faces_by_vertex_id = [[0, 1, 2, 3], [5, 6, 2, 1], [6, 7, 3, 2], [0, 4, 7, 3],
                      [0, 1, 5, 4], [4, 5, 6, 7]]

faces = []
for face_by_id in faces_by_vertex_id:
    vertices_face = []
    for point_id in face_by_id:
        vertex = vertices[point_id]
        vertices_face.append(vertex)
    face_by_vertices = Face.ByVertices(vertices_face)
    faces.append(face_by_vertices)

faces_ptr = create_stl_list(Face)
for face in faces:
    faces_ptr.push_back(face)
cc = CellComplex.ByFaces(faces_ptr, 0.0001)

class Tests(unittest.TestCase):
    """A simple cube"""
    def test_faces_cc(self):

        faces_vertical = create_stl_list(Face)
        cc.FacesVertical(faces_vertical)
        self.assertEqual(len(faces_vertical), 4)

        edges_outer = create_stl_list(Edge)
        edges_outer_top = create_stl_list(Edge)

        # four vertical outer faces
        for face in faces_vertical:
            self.assertTrue(face.IsVertical())

            # faces face out, so axis_outer and axis_outer_top should be anticlockwise
            axis_outer = face.AxisOuter()
            axis_outer_top = face.AxisOuterTop()

            edges_outer.push_back(Edge.ByStartVertexEndVertex(axis_outer[0], axis_outer[1]))
            edges_outer_top.push_back(Edge.ByStartVertexEndVertex(axis_outer_top[0], axis_outer_top[1]))

        # construct four sided wires for top and bottom
        wire_axis = Wire.ByEdges(edges_outer)
        wire_axis_top = Wire.ByEdges(edges_outer_top)

        vertices_axis = create_stl_list(Vertex)
        vertices_axis_top = create_stl_list(Vertex)

        wire_axis.Vertices(vertices_axis)
        wire_axis_top.Vertices(vertices_axis_top)

        self.assertEqual(len(vertices_axis), 4)
        self.assertEqual(len(vertices_axis_top), 4)

        face_axis = Face.ByVertices(list(vertices_axis))
        face_axis_top = Face.ByVertices(list(vertices_axis_top))

        # this should work ??!?
        #face_axis = Face.ByWire(wire_axis)
        #face_axis_top = Face.ByWire(wire_axis_top)

        normal = face_axis.Normal()
        normal_top = face_axis_top.Normal()

        # both faces are anticlockwise (normal up)
        self.assertEqual(normal.Z(), 1.0)
        self.assertEqual(normal_top.Z(), 1.0)

#output = Topology.Analyze(cc)
#print(output)

if __name__ == '__main__':
    unittest.main()
