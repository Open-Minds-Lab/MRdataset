import logging
from pathlib import Path

from bids import BIDSLayout

from MRdataset.base import BaseDataset, Run, Modality, Subject, Session
from MRdataset.config import datatypes
from MRdataset.utils import select_parameters, get_ext

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class BIDSDataset(BaseDataset):
    """
    Container to manage the properties and methods of a BIDS dataset downloaded
    from OpenNeuro. It is a subclass of Project. Expects the data_root to
    contain JSON files for reading image acquisition parameters. Use
    include_nifti_header to extract parameter from nifti headers.
    """

    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 save=True,
                 is_complete=True,
                 cache_path=None,
                 include_nifti_header=False,
                 **_kwargs):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_root : Path or str
            directory containing dicom files, supports nested hierarchies
        metadata_root : str or Path
            directory to store cache
        save : bool
            whether to save the dataset to disk
        is_complete : bool
            whether the dataset is complete
        cache_path : str or Path
            directory to store the dataset
        include_nifti_header :
            whether to check nifti headers for compliance,
            only used when --style==bids
        Examples
        --------
        >>> from MRdataset.bids_dataset import BIDSDataset
        >>> dataset = BIDSDataset()
        """

        super().__init__(name, data_root, metadata_root)
        self.is_complete = is_complete
        self.include_nifti_header = include_nifti_header
        if cache_path:
            self.cache_path = Path(cache_path)
            if save:
                self.save_dataset()

    def get_filters(self, subject: str = None,
                    session: str = None, datatype: str = None):
        """
        Given subject id, session id, and datatype, the function would create
        a dictionary to fetch the appropriate file from BIDS Layout. It just
        creates the filter dictionary, doesn't fetch the files itself.

        Parameters
        ----------
        subject : subject id
        session : session id
        datatype : one of datatypes like anat, func, dwi etc

        Returns
        -------
        Dict to specify the filter parameters
        """
        filters = {'extension': ['json']}
        if subject:
            filters['subject'] = subject
        if session:
            filters['session'] = session
        if datatype:
            filters['datatype'] = datatype
        if self.include_nifti_header:
            filters['extension'].append('nii.gz')
            filters['extension'].append('nii')
        return filters

    def walk(self):
        """
        Parses the file tree to populate them in a desirable hierarchy.
        Extracts relevant parameters and stores it in project. Creates
        a desirable hierarchy for a neuroimaging experiment
        """
        print("Started building BIDSLayout .. ")
        bids_layout = BIDSLayout(self.data_root, validate=False)
        print("Completed BIDSLayout .. ")

        filters = self.get_filters()
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

                    filters = self.get_filters(subject=nSub, datatype=datatype)
                    # {'subject': nSub,
                    #        'datatype': datatype,
                    #        'extension': 'json'}
                    session_node = self.parse(session_node,
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
                            filters = self.get_filters(subject=nSub,
                                                       session=nSess,
                                                       datatype=datatype)
                            # {'subject': nSub,
                            # 'session': nSess,
                            # 'datatype': datatype,
                            # 'extension': 'json'}
                            session_node = self.parse(session_node,
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

    def parse(self, session_node: Session,
              filters: dict, bids_layout: BIDSLayout) -> Session:
        """
        Extracts parameters for a run. Adds the new run node to session node,
        returns modified session node.

        Parameters
        ----------
        session_node : MRdataset.base.Session
            session node to which the run node has to be added
        filters : dict
            dictionary defining arguments like subject, session, datatype to
            extract corresponding files from a BIDS Layout object
        bids_layout : bids.BIDSLayout
            data structure which encapsulates the entire BIDS data structure

        Returns
        -------
        session_node : MRdataset.base.Session
            modified session_node which also contains the new run
        """
        files = bids_layout.get(**filters)
        for file in files:
            filename = file.filename
            ext = get_ext(file)
            if ext == '.json':
                parameters = select_parameters(file.path, ext)
            elif ext in ['.nii', '.nii.gz']:
                parameters = select_parameters(file.path, ext)
            else:
                raise NotImplementedError(f"Got {ext}, Expects .nii/.json")
            if parameters:
                run_node = session_node.get_run(filename)
                if run_node is None:
                    run_node = Run(filename)
                for k, v in parameters.items():
                    run_node.params[k] = v
                run_node.echo_time = round(parameters.get('EchoTime', 1.0), 4)
                session_node.add_run(run_node)
        return session_node
