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
building parts need to be constructed differently, so walls, floors,
extrusions etc. are each handled by dedicated modules.

Molior is largely derived from the Perl 'Molior' module, but has been
rewritten in python in order to interface with Topologic and
IfcOpenShell.

"""

import re
import ifcopenshell.util
from molior.extrusion import Extrusion
from molior.floor import Floor
from molior.shell import Shell
from molior.space import Space
from molior.stair import Stair
from molior.wall import Wall
from molior.repeat import Repeat

from molior.style import Style
from molior.geometry import subtract_3d, x_product_3d
from topologic import Edge, Face
from topologist.helpers import create_stl_list, string_to_coor_2d

run = ifcopenshell.api.run


class Molior:
    """A Builder, has resources to build"""

    def __init__(self, **args):
        self.file = None
        self.traces = {}
        self.hulls = {}
        self.normals = {}
        self.elevations = {}
        self.circulation = None
        self.cellcomplex = None
        self.share_dir = "share"
        self.Extrusion = Extrusion
        self.Floor = Floor
        self.Shell = Shell
        self.Space = Space
        self.Stair = Stair
        self.Wall = Wall
        self.Repeat = Repeat
        for arg in args:
            self.__dict__[arg] = args[arg]
        Molior.style = Style({"share_dir": self.share_dir})

    def execute(self):
        """Iterate through 'traces' and 'hulls' and populate an ifc 'file' object"""
        for condition in self.traces:
            for elevation in self.traces[condition]:
                level = self.elevations[elevation]
                for height in self.traces[condition][elevation]:
                    for stylename in self.traces[condition][elevation][height]:
                        for chain in self.traces[condition][elevation][height][
                            stylename
                        ]:
                            self.GetTraceIfc(
                                stylename,
                                condition,
                                level,
                                elevation,
                                height,
                                chain,
                            )
        for condition in self.hulls:
            for stylename in self.hulls[condition]:
                for hull in self.hulls[condition][stylename]:
                    self.GetHullIfc(
                        stylename,
                        condition,
                        hull,
                    )
        if self.cellcomplex:
            for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
                if item.TargetView == "MODEL_VIEW":
                    subcontext = item
            surface_lookup = {}
            # members should have been tagged with faces indices
            for member in self.file.by_type("IfcStructuralSurfaceMember"):
                pset_topology = ifcopenshell.util.element.get_psets(member).get(
                    "EPset_Topology"
                )
                if pset_topology:
                    surface_lookup[pset_topology["FaceIndex"]] = member
            edges_stl = create_stl_list(Edge)
            self.cellcomplex.Edges(edges_stl)
            for edge in list(edges_stl):
                v_start = edge.StartVertex()
                v_end = edge.EndVertex()
                start = [v_start.X(), v_start.Y(), v_start.Z()]
                end = [v_end.X(), v_end.Y(), v_end.Z()]
                connection = run(
                    "root.create_entity",
                    self.file,
                    ifc_class="IfcStructuralCurveConnection",
                    name="My Connection",
                )
                run(
                    "structural.assign_structural_analysis_model",
                    self.file,
                    product=connection,
                    structural_analysis_model=self.file.by_type(
                        "IfcStructuralAnalysisModel"
                    )[0],
                )
                if abs(start[2] - end[2]) < 0.0001:
                    connection.Axis = self.file.createIfcDirection([0.0, 0.0, 1.0])
                elif (
                    abs(start[0] - end[0]) < 0.0001 and abs(start[1] - end[1]) < 0.0001
                ):
                    connection.Axis = self.file.createIfcDirection([0.0, 1.0, 0.0])
                else:
                    vec_1 = subtract_3d(end, start)
                    vec_2 = [vec_1[1], 0.0 - vec_1[0], 0.0]
                    connection.Axis = self.file.createIfcDirection(
                        x_product_3d(vec_1, vec_2)
                    )
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=connection,
                    representation=self.file.createIfcShapeRepresentation(
                        subcontext,
                        "Reference",
                        "Edge",
                        [
                            self.file.createIfcEdge(
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(start)
                                ),
                                self.file.createIfcVertexPoint(
                                    self.file.createIfcCartesianPoint(end)
                                ),
                            )
                        ],
                    ),
                )

                faces_stl = create_stl_list(Face)
                edge.Faces(faces_stl)
                for face in list(faces_stl):
                    index = face.Get("index")
                    if index and index in surface_lookup:
                        surface_member = surface_lookup[index]
                        run(
                            "structural.add_structural_member_connection",
                            self.file,
                            relating_structural_member=surface_member,
                            related_structural_connection=connection,
                        )

    def GetTraceIfc(
        self,
        stylename,
        condition,
        level,
        elevation,
        height,
        chain,
    ):
        """Retrieves IFC data and adds to model"""
        results = []
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
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
                normal_set = "bottom"
                if re.search("^top-", condition):
                    normal_set = "top"
                vals = {
                    "closed": closed,
                    "path": path,
                    "chain": chain,
                    "circulation": self.circulation,
                    "context": subcontext,
                    "file": self.file,
                    "name": name,
                    "elevation": elevation,
                    "height": height,
                    "normals": self.normals,
                    "normal_set": normal_set,
                    "style": stylename,
                    "level": level,
                    "style_openings": myconfig["openings"],
                    "style_assets": myconfig["assets"],
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results

    def GetHullIfc(self, stylename, condition, hull):
        """Retrieves IFC data and adds to model"""
        results = []
        for item in self.file.by_type("IfcGeometricRepresentationSubContext"):
            if item.TargetView == "MODEL_VIEW":
                subcontext = item
        myconfig = Molior.style.get(stylename)
        for name in myconfig["hulls"]:
            config = myconfig["hulls"][name]
            if "condition" in config and config["condition"] == condition:
                vals = {
                    "context": subcontext,
                    "file": self.file,
                    "name": name,
                    "style": stylename,
                    "hull": hull,
                }
                vals.update(config)
                part = getattr(self, config["class"])(vals)

                part.execute()
                # results are only used by test suite
                results.append(part)
        return results
