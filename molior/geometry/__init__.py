from math import sqrt, pi, atan, cos, sin
import numpy


def matrix_transform(theta, coor):
    """A transform matrix from a rotation in the XY plane and an XYZ shift"""
    return numpy.array(
        [
            [cos(theta), 0 - sin(theta), 0.0, coor[0]],
            [sin(theta), cos(theta), 0.0, coor[1]],
            [0.0, 0.0, 1.0, coor[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def matrix_align(A, B):
    """A transform matrix that moves to A and 2D rotates to align the X axis to B"""
    v = normalise_2d(subtract_2d(B, A))
    return numpy.array(
        [
            [v[0], 0 - v[1], 0.0, A[0]],
            [v[1], v[0], 0.0, A[1]],
            [0.0, 0.0, 1.0, A[2]],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def transform(matrix, A):
    """Transform a 2d or 3d vector using a 4x4 matrix"""
    if len(A) == 3:
        vertex = numpy.array([[*A, 1.0]]).T
        result = matrix @ vertex
        return result.T.tolist()[0][:3]
    elif len(A) == 2:
        vertex = numpy.array([[*A, 0.0, 1.0]]).T
        result = matrix @ vertex
        return result.T.tolist()[0][:2]


def map_to_2d(vertices, normal_vector):
    """Transform 3d nodes and their normal to 2d nodes, a return matrix and a vertical vector"""

    # coordinates need to be vertical in 4 high matrix
    nodes_3d = numpy.array([[*vertex, 1.0] for vertex in vertices]).T

    # normal has to be a 1x4 matrix
    normal = [[normal_vector[0]], [normal_vector[1]], [normal_vector[2]], [1.0]]

    # rotate around z axis
    normal_z = normalise_2d([normal[0][0], normal[1][0]])
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
    nodes_2d_tmp = zx_rot_inv @ nodes_3d

    # shift to origin
    origin_matrix = numpy.array(
        [
            [1.0, 0.0, 0.0, 0 - nodes_2d_tmp[0][0]],
            [0.0, 1.0, 0.0, 0 - nodes_2d_tmp[1][0]],
            [0.0, 0.0, 1.0, 0 - nodes_2d_tmp[2][0]],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    # combined rotation, rotation and shift
    combined_inv = origin_matrix @ zx_rot_inv
    combined = numpy.linalg.inv(combined_inv)

    # outline of roof shifted and rotated to z=0 plane
    nodes_2d = [
        [float(node[0]), float(node[1]), 0.0]
        for node in numpy.transpose(combined_inv @ nodes_3d)
    ]

    return nodes_2d, combined, [normal_x[0][0], normal_x[1][0], normal_x[2][0]]


# FIXME replace these with appropriate numpy functions


def add_2d(A, B):
    return [A[0] + B[0], A[1] + B[1]]


def angle_2d(A, B):
    if A[0] == B[0] and A[1] <= B[1]:
        return pi / 2
    if A[0] == B[0] and A[1] > B[1]:
        return pi / -2
    radians = atan((B[1] - A[1]) / (B[0] - A[0]))
    if B[0] < A[0]:
        radians += pi
    return radians


def distance_2d(A, B):
    return sqrt((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2)


def line_intersection(line_0, line_1):
    if line_0["a"] == line_1["a"]:
        return None
    x = (line_1["b"] - line_0["b"]) / (line_0["a"] - line_1["a"])
    y = (line_0["a"] * x) + line_0["b"]
    return [x, y]


def normalise_2d(A):
    length = distance_2d([0.0, 0.0], A)
    if length == 0.0:
        return [1.0, 0.0]
    return [A[0] / length, A[1] / length]


def points_2line(A, B):
    vector = subtract_2d(B, A)
    if vector[0] == 0.0:
        vector[0] = 0.00000000001
    a = vector[1] / vector[0]
    b = A[1] - (A[0] * a)
    return {"a": a, "b": b}


def scale_2d(A, B):
    if type(A) == list:
        return [A[0] * B, A[1] * B]
    return [B[0] * A, B[1] * A]


def subtract_2d(A, B):
    return [A[0] - B[0], A[1] - B[1]]


def x_product_3d(A, B):
    x = A[1] * B[2] - B[1] * A[2]
    y = A[2] * B[0] - B[2] * A[0]
    z = A[0] * B[1] - B[0] * A[1]
    return normalise_3d([x, y, z])


def normalise_3d(A):
    magnitude = magnitude_3d(A)
    if magnitude == 0.0:
        return [1.0, 0.0, 0.0]
    return scale_3d(A, 1.0 / magnitude)


def magnitude_3d(A):
    return distance_3d([0.0, 0.0, 0.0], A)


def scale_3d(A, B):
    if type(A) == list:
        return [A[0] * B, A[1] * B, A[2] * B]
    return [B[0] * A, B[1] * A, B[2] * A]


def subtract_3d(A, B):
    return [A[0] - B[0], A[1] - B[1], A[2] - B[2]]


def add_3d(A, B):
    return [A[0] + B[0], A[1] + B[1], A[2] + B[2]]


def distance_3d(A, B):
    return sqrt((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2 + (A[2] - B[2]) ** 2)
