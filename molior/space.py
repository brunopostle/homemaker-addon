import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass


class Space(BaseClass):
    """A room or outdoor volume, as a 2D path extruded vertically"""

    def __init__(self, args={}):
        super().__init__(args)
        self.ceiling = 0.2
        self.colour = 255
        self.floor = 0.02
        self.id = ""
        self.ifc = "IFCSPACE"
        self.inner = 0.08
        self.path = []
        self.type = "molior-space"
        self.usage = ""
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.usage = self.name
        # FIXME identify cell and set colour
        # if not cell.IsOutside():
        #    crinkliness = cell.Crinkliness()
        #    colour = (int(crinkliness*16)-7)*10
        #    if colour > 170: colour = 170
        #    if colour < 10: colour = 10
        # FIXME cell[index] can be used for id
