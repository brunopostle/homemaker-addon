import os
import sys
import ifcopenshell.api
import numpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import normalise_2d
from topologist.helpers import string_to_coor

run = ifcopenshell.api.run


class Shell(BaseClass):
    """A pitched roof or soffit"""

    def __init__(self, args={}):
        super().__init__(args)
        self.id = ""
        self.ifc = "IFCROOF"
        self.inner = 0.08
        self.outer = 0.20
        self.type = "molior-shell"
        for arg in args:
            self.__dict__[arg] = args[arg]

    def Ifc(self, ifc, context):
        """Generate some ifc"""
        for face in self.hull.faces:
            # coordinates need to be vertical in 4x4 matrix
            nodes = numpy.array(
                [[*string_to_coor(node_str), 1.0] for node_str in face[0]]
            )
            nodes = numpy.transpose(nodes)

            # normal has to be a 1x4 matrix
            normal = [[face[1][0]], [face[1][1]], [face[1][2]], [1.0]]

            # rotate around z axis
            normal_z = normalise_2d([face[1][0], face[1][1]])
            z_rot_mat = numpy.array(
                [
                    [0 - normal_z[1], 0 - normal_z[0], 0.0, 0.0],
                    [normal_z[0], 0 - normal_z[1], 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
            z_rot_inv = numpy.linalg.inv(z_rot_mat)

            # rotate around x axis
            normal_x = z_rot_inv @ normal
            x_rot_mat = numpy.array(
                [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, normal_x[2][0], normal_x[1][0], 0.0],
                    [0.0, 0 - normal_x[1][0], normal_x[2][0], 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
            x_rot_inv = numpy.linalg.inv(x_rot_mat)

            # combined rotation and rotation
            zx_rot_inv = x_rot_inv @ z_rot_inv

            # face rotated to horizontal, but not necessarily z=0
            nodes_2d_tmp = zx_rot_inv @ nodes

            # shift in z axis
            z_shift = nodes_2d_tmp[2][0]
            z_shift_mat = numpy.array(
                [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0 - z_shift],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )

            # combined rotation, rotation and shift
            combined_inv = z_shift_mat @ zx_rot_inv
            combined = numpy.linalg.inv(combined_inv)

            # outline of roof shifted and rotated to z=0 plane
            nodes_2d = [
                [float(node[0]), float(node[1]), 0.0]
                for node in numpy.transpose(combined_inv @ nodes)
            ]

            entity = run("root.create_entity", ifc, ifc_class=self.ifc, name="MyShell")
            # FIXME this puts roofs in the ground floor
            ifc.assign_storey_byindex(entity, 0)
            if abs(float(normal_x[2][0])) < 0.001:
                extrude_height = self.outer
                extrude_direction = [0.0, 0.0, 1.0]
            else:
                extrude_height = self.outer / float(normal_x[2][0])
                extrude_direction = [
                    0.0,
                    0 - float(normal_x[1][0]),
                    float(normal_x[2][0]),
                ]
            shape = ifc.createIfcShapeRepresentation(
                context,
                "Body",
                "SweptSolid",
                [
                    ifc.createExtrudedAreaSolid(
                        nodes_2d,
                        extrude_height,
                        extrude_direction,
                    )
                ],
            )
            run(
                "geometry.assign_representation",
                ifc,
                product=entity,
                representation=shape,
            )
            run(
                "geometry.edit_object_placement",
                ifc,
                product=entity,
                matrix=combined,
            )
