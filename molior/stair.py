import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from molior.baseclass import Molior

class Stair(Molior):
    """a stair filling a single storey extruded space"""
    def __init__(self, args = {}):
        super().__init__(args)
        self.ceiling = 0.2
        self.colour = 255
        self.corners_in_use = []
        self.floor = 0.02
        self.going = 0.25
        self.id = ''
        self.inner = 0.08
        self.path = []
        self.risers = 0
        self.type = 'molior-stair'
        self.usage = ''
        self.width = 1.0
        for arg in args:
            self.__dict__[arg] = args[arg]