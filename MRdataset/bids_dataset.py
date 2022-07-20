import json
import logging
from pathlib import Path

from bids import BIDSLayout

from MRdataset.base import Project, Run, Modality, Subject, Session
from MRdataset.config import PARAMETER_NAMES

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class BidsDataset(Project):
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
        >>> from MRdataset.bids_dataset import BidsDataset
        >>> dataset = BidsDataset()
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
        for datatype in ('anat', 'func', 'dwi'):
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
                    logger.info("No sessions found! Using a default name")

                else:
                    # If there are sessions
                    for nSess in layout_sessions:
                        session_node = subject_obj.get_session(nSess)
                        if session_node is None:
                            session_node = Session(nSess)
                        for nRun in bids_layout.get_runs(subject=nSub,
                                                         session=nSess):
                            run_node = session_node.get_run(nRun)
                            if run_node is None:
                                run_node = Run(nRun)
                            filters = {'subject': nSub,
                                       'session': nSess,
                                       'run': nRun,
                                       'datatype': datatype,
                                       'extension': 'json'}
                            files = bids_layout.get(**filters)

                            if not files:
                                continue
                            with open(files[0], "r") as read_file:
                                parameters = json.load(read_file)

                            # TODO files is a list, what if there are differences??
                            # default = None
                            # for file in files:
                            #     with open(file, "r") as read_file:
                            #         parameters = json.load(read_file)
                            #     if not default:
                            #         default = parameters.copy()
                            #     else:
                            selected_params = dict()
                            for key in parameters:
                                for entry in PARAMETER_NAMES:
                                    if entry.lower() in key.lower():
                                        selected_params[key] = parameters[key]

                            run_node.params = selected_params.copy()
                            run_node.echo_time = parameters.get('EchoTime', 1.0)
                            session_node.add_run(run_node)
                            subject_obj.add_session(session_node)
                            modality_obj.add_subject(subject_obj)
                            self.add_modality(modality_obj)
