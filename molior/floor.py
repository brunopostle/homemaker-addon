import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from molior.baseclass import BaseClass

class Floor(BaseClass):
    """A floor filling a room or space"""
    def __init__(self, args = {}):
        super().__init__(args)
        self.floor = 0.02
        self.id = ''
        self.inner = 0.08
        self.path = []
        self.type = 'molior-floor'
        for arg in args:
            self.__dict__[arg] = args[arg]
