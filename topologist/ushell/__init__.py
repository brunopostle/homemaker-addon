from ..helpers import string_to_coor


class shell:
    """A simple append-only 3D shell"""

    # Note, ideally this would be represented by a Topologic Shell.  But
    # Shells don't support arbitrary dictionary references to python
    # objects such as Topologic Cells and Faces in the CellComplex

    def __init__(self):
        self.nodes = {}
        self.faces = []

    @staticmethod
    def _node_to_key(node):
        """Convert node coordinates to a string key"""
        return f"{node[0]}__{node[1]}__{node[2]}"

    @staticmethod
    def _nodes_to_keys(node_coors):
        """Convert a list of node coordinates to string keys"""
        return [shell._node_to_key(node) for node in node_coors]

    def add_facet(self, node_coors, data):
        """
        Add a face to this shell

        Args:
            node_coors: List of 3D coordinates for the face vertices
            data: Associated data for the face
        """
        nodes_str = self._nodes_to_keys(node_coors)
        my_face = [nodes_str, data, None]
        self.faces.append(my_face)

        for node_key in nodes_str:
            if node_key not in self.nodes:
                self.nodes[node_key] = []
            self.nodes[node_key].append(my_face)

    # FIXME doesn't appear to be in use
    def nodes_all(self):
        """Get a list of node coordinates for export"""
        return [string_to_coor(node) for node in self.nodes]

    # FIXME doesn't appear to be in use
    def faces_all(self):
        """Get a list of faces as node ids for export"""
        nodes = list(self.nodes)
        return [[nodes.index(vertex) for vertex in face[0]] for face in self.faces]

    def segment(self):
        """
        Utility to allocate index numbers to faces by contiguous region.
        Uses a breadth-first traversal to identify connected components.
        """
        if not self.faces:
            return

        # Reset all face groups
        for face in self.faces:
            face[2] = None

        current_group = 0

        # Process each face
        for start_face in self.faces:
            # Skip faces that have already been assigned to a group
            if start_face[2] is not None:
                continue

            # Start a new connected component
            start_face[2] = current_group
            queue = [start_face]

            # Breadth-first traversal
            while queue:
                current_face = queue.pop(0)

                # Find all adjacent faces through shared nodes
                for node_key in current_face[0]:
                    for adjacent_face in self.nodes[node_key]:
                        if adjacent_face[2] is None:
                            adjacent_face[2] = current_group
                            queue.append(adjacent_face)

            current_group += 1

    def decompose(self):
        """
        Identify contiguous regions and return a list of new shells

        Returns:
            list: List of shell objects, each representing a contiguous region
        """
        self.segment()
        results = {}
        for face in self.faces:
            group = face[2]
            if group not in results:
                results[group] = shell()

            # Convert node strings back to coordinates
            node_coords = [string_to_coor(node_str) for node_str in face[0]]
            results[group].add_facet(node_coords, face[1])

        return list(results.values())
