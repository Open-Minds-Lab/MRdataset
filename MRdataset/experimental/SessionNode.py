from MRdataset.experimental import Node


class SessionNode(Node.Node):
    def __init__(self):
        super().__init__()
        self.consistent = None

    def isconsistent(self):
        if self.consistent is None:
            anchor = self.children[0]
            for k in self.children[1:]:
                if anchor != k:
                    self.consistent = False
                    return self.consistent
            self.consistent = True
        return self.consistent

    def populate(self):
        if self.isconsistent():
            self.fparams = self.children[0].fparams
        else:
            print("Inconsistency detected in session. Please check.")


