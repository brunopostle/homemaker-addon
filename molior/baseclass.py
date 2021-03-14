class BaseClass():
    """A generic building object"""
    def __init__(self, args = {}):
        self.closed = 1
        self.elevation = 0.0
        self.guid = 'my building'
        self.height = 0.0
        self.level = 0
        self.name = 'base-class'
        self.plot = 'my plot'
        self.style = 'default'
        for arg in args:
            self.__dict__[arg] = args[arg]
