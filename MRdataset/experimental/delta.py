from MRdataset.modules import xnatdataset
from MRdataset.experimental import dicom_node, session_node, subject_node, node
from sys import getsizeof


class ProjectTree(node.Node):
    def __init__(self, dataset):
        super().__init__()
        self.dataset = dataset
        self._construct_tree()

    def _construct_tree(self):
        for sid in self.dataset.subjects:
            sub = subject_node.SubjectNode()
            for sess in self.dataset.sessions[sid]:
                data = self.dataset[sid, sess]
                session_node = self._construct_session(data['files'])
                session_node.populate()
                sub.add(session_node)
            sub.populate()
            self.add(sub)

    def _construct_session(self, files):
        sess = session_node.SessionNode()
        for f in files:
            d = dicom_node.DicomNode(f)
            sess.add(d)
        return sess

    def isconsistent(self):
        pass

if __name__ == "__main__":
    dataset = xnatdataset.XnatDataset()
    tree = ProjectTree(dataset)

