from collections import defaultdict

class Node:
    def __init__(self):
        self.fparams = defaultdict(list)
        self.children = []
        self.verbose = False

    def add(self, other):
        self.children.append(other)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return NotImplemented
        if self.fparams is None:
            raise TypeError("Parameters expected, not NoneType for Node at index 0.")
        if other.fparams is None:
            raise TypeError("Parameters expected, not NoneType for Node at index 0.")
        for k in self.fparams:
            if self.fparams[k] != other.fparams[k]:
                return False
        return True

    def populate(self, *args, **kwargs):
        pass
