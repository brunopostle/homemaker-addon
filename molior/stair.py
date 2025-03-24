from .baseclass import TraceClass


class Stair(TraceClass):
    """a stair filling a single storey extruded space"""

    def __init__(self, args=None):
        args = args or {}
        super().__init__(args)
        self.ceiling = 0.2
        self.corners_in_use = []
        self.floor = 0.02
        self.going = 0.25
        self.ifc = "IfcStair"
        self.inner = 0.08
        self.path = []
        self.riser = 0.19
        self.usage = ""
        self.width = 1.0
        for arg in args:
            self.__dict__[arg] = args[arg]
        self.risers = (int(self.height / self.riser) + 1,)
        # FIXME check circulation graph, only draw stair if cell above this cell is stair

    def execute(self):
        """Generate some ifc"""
        # TODO entire stair drawing module still needs porting from Perl Molior library
        pass
