from MRdataset.experimental import Node


class SubjectNode(Node.Node):
    def __init__(self):
        super().__init__()

    def populate(self, *args, **kwargs):
        for k in self.children:
            self.fparams.append(k.fparams)

