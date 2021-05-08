from topologist.helpers import string_to_coor


class shell:
    """A simple append-only 3D shell"""

    def __init__(self):
        self.nodes = {}
        self.faces = []

    def add_face(self, node_coors, normal, data):
        """add a face to this shell"""
        nodes_str = [
            str(node[0]) + "__" + str(node[1]) + "__" + str(node[2])
            for node in node_coors
        ]
        my_face = [nodes_str, normal, data, None]
        self.faces.append(my_face)
        for index in range(len(node_coors)):
            if not nodes_str[index] in self.nodes:
                self.nodes[nodes_str[index]] = []
            self.nodes[nodes_str[index]].append(my_face)

    def nodes_all(self):
        """get a list of node coordinates for export"""
        return [string_to_coor(node) for node in list(self.nodes)]

    def faces_all(self):
        """get a list of faces as node ids for export"""
        faces = []
        nodes = list(self.nodes)
        for face in self.faces:
            faces.append([nodes.index(vertex) for vertex in face[0]])
        return faces

    def segment(self):
        """allocate index numbers to faces by contiguous region"""
        if self.faces[0][3] == None:
            # put first face in group 0
            self.faces[0][3] = 0
        indices_in_use = {}
        dirty = True
        while dirty == True:
            dirty = False
            for face in self.faces:
                if face[3] == None:
                    for node_str in face[0]:
                        node = self.nodes[node_str]
                        for face_ref in node:
                            if not face_ref[3] == None:
                                face[3] = face_ref[3]
                                dirty = True
                                continue
                else:
                    indices_in_use[face[3]] = True
        index = len(list(indices_in_use))
        for face in self.faces:
            if face[3] == None:
                face[3] = index
                self.segment()

    def decompose(self):
        """identify contiguous regions and return a list of new shells"""
        self.segment()
        results = {}
        for face in self.faces:
            group = face[3]
            if not group in results:
                results[group] = shell()
            results[group].add_face(
                [string_to_coor(node_str) for node_str in face[0]], face[1], face[2]
            )
        return list(results.values())
