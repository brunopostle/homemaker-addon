from math import sqrt, pi, atan


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


def is_between_2d(P, A, B):
    length = distance_2d(A, B)
    length_A = distance_2d(A, P)
    length_B = distance_2d(B, P)
    if abs(length - length_A - length_B) < 0.000001:
        return True
    return False


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
    if A.__class__ == [].__class__:
        return [A[0] * B, A[1] * B]
    return [B[0] * A, B[1] * A]


def subtract_2d(A, B):
    return [A[0] - B[0], A[1] - B[1]]
