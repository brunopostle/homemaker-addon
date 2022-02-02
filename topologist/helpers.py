def el(elevation):
    if elevation >= 0.0:
        return int((elevation * 1000) + 0.5) / 1000
    return int((elevation * 1000) - 0.5) / 1000


def string_to_coor(string):
    return [float(num) for num in string.split("__")]
