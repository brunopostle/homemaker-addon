from topologist.helpers import string_to_coor


class shell:
    """A simple append-only 3D shell"""

    # Note, ideally this would be represented by a Topologic Shell.  But
    # Shells don't support arbitrary dictionary references to python
    # objects such as Topologic Cells and Faces in the CellComplex

    def __init__(self):
        self.nodes = {}
        self.faces = []

    def add_facet(self, node_coors, data):
        """add a face to this shell"""
        nodes_str = [
            str(node[0]) + "__" + str(node[1]) + "__" + str(node[2])
            for node in node_coors
        ]
        my_face = [nodes_str, data, None]
        self.faces.append(my_face)
        for index in range(len(node_coors)):
            if not nodes_str[index] in self.nodes:
                self.nodes[nodes_str[index]] = []
            self.nodes[nodes_str[index]].append(my_face)

    # FIXME doesn't appear to be in use
    def nodes_all(self):
        """get a list of node coordinates for export"""
        return [string_to_coor(node) for node in list(self.nodes)]

    # FIXME doesn't appear to be in use
    def faces_all(self):
        """get a list of faces as node ids for export"""
        faces = []
        nodes = list(self.nodes)
        for face in self.faces:
            faces.append([nodes.index(vertex) for vertex in face[0]])
        return faces

    def segment(self):
        """allocate index numbers to faces by contiguous region"""
        if self.faces[0][2] == None:
            # put first face in group 0
            self.faces[0][2] = 0
        indices_in_use = {}
        dirty = True
        while dirty == True:
            dirty = False
            for face in self.faces:
                if face[2] == None:
                    for node_str in face[0]:
                        node = self.nodes[node_str]
                        for face_ref in node:
                            if not face_ref[2] == None:
                                face[2] = face_ref[2]
                                dirty = True
                                continue
                else:
                    indices_in_use[face[2]] = True
        index = len(list(indices_in_use))
        for face in self.faces:
            if face[2] == None:
                face[2] = index
                self.segment()

    def decompose(self):
        """identify contiguous regions and return a list of new shells"""
        self.segment()
        results = {}
        for face in self.faces:
            group = face[2]
            if not group in results:
                results[group] = shell()
            results[group].add_facet(
                [string_to_coor(node_str) for node_str in face[0]], face[1]
            )
        return list(results.values())
