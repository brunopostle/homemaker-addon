from topologic import GlobalCluster


def el(elevation):
    if elevation >= 0.0:
        return int((elevation * 1000) + 0.5) / 1000
    return int((elevation * 1000) - 0.5) / 1000


def string_to_coor(string):
    return [float(num) for num in string.split("__")]


def string_to_coor_2d(string):
    return string_to_coor(string)[0:2]


def wipe_global_cluster(keep_topologies):
    global_cluster = GlobalCluster.GetInstance()
    sub_topologies = []
    global_cluster.SubTopologies(sub_topologies)
    if len(sub_topologies) == 0:
        # workaround Linux bug where SubTopologies reports nothing
        return
    for sub_topology in sub_topologies:
        global_cluster.RemoveTopology(sub_topology)
    for keep_topology in keep_topologies:
        global_cluster.AddTopology(keep_topology)
