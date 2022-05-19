from MRdataset.experimental import node


class SubjectNode(node.Node):
    def __init__(self):
        super().__init__()

    def populate(self, *args, **kwargs):
        for session in self.children:
            if session.isconsistent():
                self.fparams[session.filepath] = session.fparams

