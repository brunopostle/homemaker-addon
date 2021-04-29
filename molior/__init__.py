"""Molior builds 3D models from topologist 'traces'

Traces are 2D closed or open chains that define building elements,
differentiated by elevation, height and style properties, typically
running in an anti-clockwise direction, these follow the outlines of
rooms, walls, eaves, string-courses etc.

Which traces are used, and how they are used, are defined by files in
the 'molior/style/share' folder and subfolders.  Each subfolder has a unique
name and represents a different architectural 'style', buildings can be
all one style or have multiple styles, each applied to different parts
of the building.  Styles are inherited from parent folders, and can
represent only minor variations, without needing to duplicate anything
that is already defined by the parent folder(s).  Access to these style
definitions is handled by the molior.style module.

Molior uses IfcOpenShell to generate IFC models of buildings, with some
extra helper methods defined in the molior.ifc module.  Different
building parts need to be constructed differently, so walls, ceilings,
extrusions etc. are each handled by dedicated modules.

Molior is largely derived from the Perl 'Molior' module, but has been
rewritten in python in order to interface with Topologic and
IfcOpenShell.

"""

from molior.ceiling import Ceiling
from molior.extrusion import Extrusion
from molior.floor import Floor
from molior.space import Space
from molior.stair import Stair
from molior.wall import Wall
from molior.style import Style
from topologist.helpers import string_to_coor_2d


class Molior:
    """A Builder, has resources to build"""

    def __init__(self, args={}):
        # TODO enable user defined location for share_dir
        self.share_dir = "share"
        self.Ceiling = Ceiling
        self.Extrusion = Extrusion
        self.Floor = Floor
        self.Space = Space
        self.Stair = Stair
        self.Wall = Wall
        for arg in args:
            self.__dict__[arg] = args[arg]
        Molior.style = Style({"share_dir": self.share_dir})

    def Process(self, ifc, circulation, elevations, traces):
        for condition in traces:
            for elevation in traces[condition]:
                level = elevations[elevation]
                for height in traces[condition][elevation]:
                    for stylename in traces[condition][elevation][height]:
                        for chain in traces[condition][elevation][height][stylename]:
                            self.GetIfc(
                                ifc,
                                stylename,
                                condition,
                                level,
                                elevation,
                                height,
                                chain,
                                circulation,
                            )

    def GetIfc(
        self, ifc, stylename, condition, level, elevation, height, chain, circulation
    ):
        """Retrieves IFC data and adds to model"""
        results = []
        for item in ifc.by_type("IfcGeometricRepresentationSubContext"):
            if item.TargetView == "MODEL_VIEW":
                subcontext = item
        myconfig = Molior.style.get(stylename)
        for name in myconfig["traces"]:
            config = myconfig["traces"][name]
            if "condition" in config and config["condition"] == condition:
                closed = 0
                if chain.is_simple_cycle():
                    closed = 1
                path = []
                for node in chain.nodes():
                    path.append(string_to_coor_2d(node))

                # TODO style definition should set material, layerset and/or
                # colour for generated products.  Resources such as windows and
                # doors in an IFC library should reference materials independently
                vals = {
                    "closed": closed,
                    "path": path,
                    "chain": chain,
                    "circulation": circulation,
                    "name": name,
                    "elevation": elevation,
                    "height": height,
                    "style": stylename,
                    "level": level,
                    "style_openings": myconfig["openings"],
                    "style_assets": myconfig["assets"],
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                part.Ifc(ifc, subcontext)
                # results are only used by test suite
                results.append(part)
        return results
