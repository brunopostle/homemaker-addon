import cppyy


def create_stl_list(cppyy_data_type):
    return cppyy.gbl.std.list[cppyy_data_type.Ptr]()


def el(elevation):
    if elevation >= 0.0:
        return int((elevation * 1000) + 0.5) / 1000
    return int((elevation * 1000) - 0.5) / 1000


def string_to_coor(string):
    return [float(num) for num in string.split("__")]


def string_to_coor_2d(string):
    return string_to_coor(string)[0:2]
