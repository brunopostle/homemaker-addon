import os
import yaml

from molior.ceiling import Ceiling
from molior.extrusion import Extrusion
from molior.floor import Floor
from molior.insert import Insert
from molior.space import Space
from molior.stair import Stair
from molior.wall import Wall
from topologist.helpers import string_to_coor_2d


class Molior:
    """A Builder, has resources to build"""

    def __init__(self, args={}):
        self.share_dir = "share"
        self.Ceiling = Ceiling
        self.Extrusion = Extrusion
        self.Floor = Floor
        self.Insert = Insert
        self.Space = Space
        self.Stair = Stair
        self.Wall = Wall
        for arg in args:
            self.__dict__[arg] = args[arg]
        share_dir_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), self.share_dir)
        )
        # FIXME needs method to assemble and cache a style config from style name using inheritance
        style_path = os.path.join(share_dir_path, "style.yml")
        style_fh = open(style_path, "rb")
        self.config = yaml.safe_load(style_fh.read())
        style_fh.close()

    def GetMolior(self, style, condition, level, elevation, height, chain, circulation):
        """Retrieves a struct that can be passed to the molior-ifc.pl command-line tool to generate an IFC file"""
        results = []
        for name in self.config:
            config = self.config[name]
            if "condition" in config and config["condition"] == condition:
                closed = 0
                if chain.is_simple_cycle():
                    closed = 1
                path = []
                for node in chain.nodes():
                    path.append(string_to_coor_2d(node))

                vals = {
                    "closed": closed,
                    "path": path,
                    "name": name,
                    "elevation": elevation,
                    "height": height,
                    "style": style,
                    "level": level,
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                # part may be a wall, add some openings
                if "do_populate_exterior_openings" in part.__dict__:
                    edges = chain.edges()
                    for segment in range(len(part.openings)):
                        edge = chain.graph[edges[segment][0]]
                        face = edge[1][2]
                        try:
                            interior_type = face.UsageInside()
                        except:
                            interior_type = "toilet"
                        part.populate_exterior_openings(segment, interior_type, 0)
                elif "do_populate_interior_openings" in part.__dict__:
                    edge = chain.graph[chain.edges()[0][0]]
                    face = edge[1][2]
                    vertex = face.GraphVertex(circulation)
                    if vertex != None:
                        usages = face.Usages()
                        part.populate_interior_openings(0, usages[0], usages[1], 0)

                results.append(part)
        return results

    def GetIfc(style, condition, level, elevation, height, chain):
        """Retrieves IFC data directly without using molior-ifc.pl"""
        # TODO
        pass
