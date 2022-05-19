from MRdataset.experimental import node
import pathlib
from collections import defaultdict


class SessionNode(node.Node):
    def __init__(self):
        super().__init__()
        self.consistent = None

    def isconsistent(self):
        if self.consistent is None:
            anchor = self.children[0]
            for k in self.children[1:]:
                assert pathlib.Path(k.filepath).parent == pathlib.Path(anchor.filepath).parent, \
                    "Comparing dicom files from different folders. Why? "
                if anchor != k:
                    self.consistent = False
                    # diff['files'] = [k.filepath, anchor.filepath]
                    # diff['params'] =
                    # return self.consistent
            # self.consistent = True
            # After for loop, self.consistent remained NoneType. Therefore, files are good.
            if self.consistent is None:
                self.consistent = True
        return self.consistent

    def populate(self):
        self.filepath = pathlib.Path(self.children[0].filepath).parent
        if self.isconsistent():
            self.fparams = self.children[0].fparams
            print("Consistent session : {0}".format(self.filepath))
        else:
            print("Inconsistency detected in session. Please check {0}".format(self.filepath))
        # After testing consistency, kill all children to save spac
        self.children.clear()
        self.children = None



