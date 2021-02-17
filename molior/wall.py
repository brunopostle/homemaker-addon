import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from molior.baseclass import Molior

class Wall(Molior):
    """A vertical wall, internal or external"""
    def __init__(self, args = {}):
        super().__init__(args)
        self.bounds = []
        self.ceiling = 0.35
        self.closed = 0
        self.extension = 0.25
        self.floor = 0.02
        self.inner = 0.08
        self.openings = []
        self.outer = 0.25
        self.path = []
        self.type = 'molior-wall'
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.init_openings()

    def init_openings(self):
        segments = len(self.path)
        if not self.closed:
            segments -= 1
        if len(self.openings) == segments:
            return
        self.openings = []
        for index in range(segments):
            self.openings.append([])

    def populate_exterior_openings(self, segment_id, interior_type, access):
        if interior_type == 'Living' or interior_type == 'Retail':
            self.openings[segment_id].append({'name': 'living outside window', 'along': 0.5, 'size': 0})
        if interior_type == 'Toilet':
            self.openings[segment_id].append({'name': 'toilet outside window', 'along': 0.5, 'size': 0})
        if interior_type == 'Kitchen':
            self.openings[segment_id].append({'name': 'kitchen outside window', 'along': 0.5, 'size': 0})
        if interior_type == 'Bedroom':
            self.openings[segment_id].append({'name': 'bedroom outside window', 'along': 0.5, 'size': 0})
        if interior_type == 'Circulation' or interior_type == 'Circulation_stair':
            self.openings[segment_id].append({'name': 'circulation outside window', 'along': 0.5, 'size': 0})
        if interior_type == 'Retail' and self.level == 0:
            self.openings[segment_id].append({'name': 'retail entrance', 'along': 0.5, 'size': 0})
        if interior_type == 'Circulation' and self.level == 0:
            self.openings[segment_id].append({'name': 'house entrance', 'along': 0.5, 'size': 0})
        if interior_type != 'Toilet' and access == 1:
            self.openings[segment_id].append({'name': 'living outside door', 'along': 0.5, 'size': 0})

    def populate_interior_openings(self, segment_id, type_a, type_b, access):
        self.openings[segment_id].append({'name': 'living inside door', 'along': 0.5, 'size': 0})
