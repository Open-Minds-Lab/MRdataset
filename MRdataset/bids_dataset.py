import logging
from pathlib import Path

from MRdataset.base import Project, Run, Modality, Subject, Session
from MRdataset.config import datatypes
from MRdataset.utils import select_parameters
from bids import BIDSLayout

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class BIDSDataset(Project):
    """

    """

    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 include_phantom=False,
                 reindex=False):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_root : Path or str
            directory containing dicom files, supports nested hierarchies
        metadata_root : str or Path
            directory to store cache
        include_phantom : bool
            whether to include localizer/aahead_scout/phantom/acr
        reindex : bool
            If true, rejects stored cache and rebuilds index

        Examples
        --------
        >>> from MRdataset.bids_dataset import BIDSDataset
        >>> dataset = BIDSDataset()
        """

        super().__init__(name, data_root, metadata_root)

        self.include_phantom = include_phantom
        indexed = self.cache_path.exists()
        if not indexed or reindex:
            self.walk()
            self.save_dataset()
        else:
            self.load_dataset()

    def walk(self):
        """parses the file tree to populate them in a desirable hierarchy"""
        bids_layout = BIDSLayout(self.data_root)

        filters = {'extension': 'json'}
        if not bids_layout.get(**filters):
            raise EOFError('No JSON files found at --data_root {}'.format(
                self.data_root))

        for datatype in datatypes:
            modality_obj = self.get_modality(datatype)
            if modality_obj is None:
                modality_obj = Modality(datatype)

            layout_subjects = bids_layout.get_subjects()
            if not layout_subjects:
                raise EOFError("No Subjects found in dataset")
            for nSub in layout_subjects:
                subject_obj = modality_obj.get_subject(nSub)
                if subject_obj is None:
                    subject_obj = Subject(nSub)

                layout_sessions = bids_layout.get_sessions(subject=nSub)

                if not layout_sessions:
                    logger.info("No sessions found. '1' is default "
                                "session name")
                    session_node = subject_obj.get_session('1')
                    if session_node is None:
                        session_node = Session('1')

                    filters = {'subject': nSub,
                               'datatype': datatype,
                               'extension': 'json'}
                    session_node = self.parse_json(session_node,
                                                   filters,
                                                   bids_layout)
                    if session_node.runs:
                        subject_obj.add_session(session_node)
                else:
                    # If there are sessions
                    for nSess in layout_sessions:
                        session_node = subject_obj.get_session(nSess)
                        if session_node is None:
                            session_node = Session(nSess)
                            filters = {'subject': nSub,
                                       'session': nSess,
                                       'datatype': datatype,
                                       'extension': 'json'}
                            session_node = self.parse_json(session_node,
                                                           filters,
                                                           bids_layout)
                        if session_node.runs:
                            subject_obj.add_session(session_node)
                if subject_obj.sessions:
                    modality_obj.add_subject(subject_obj)
            if modality_obj.subjects:
                self.add_modality(modality_obj)
        if not self.modalities:
            raise EOFError("Expected Sidecar JSON files in --data_root. Got 0")

    def parse_json(self, session_node, filters, bids_layout):
        files = bids_layout.get(**filters)
        for file in files:
            filename = file.filename
            parameters = select_parameters(file.path)
            if parameters:
                run_node = session_node.get_run(filename)
                if run_node is None:
                    run_node = Run(filename)
                run_node.params = parameters.copy()
                run_node.echo_time = parameters.get('EchoTime', 1.0)
                session_node.add_run(run_node)
        return session_node
