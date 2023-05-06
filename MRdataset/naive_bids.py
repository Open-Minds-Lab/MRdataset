"""BIDS dataset class for MRdataset"""
from bids import BIDSLayout

from MRdataset.base import BaseDataset, Run, Modality, Subject, Session
from MRdataset.config import VALID_DATATYPES
from MRdataset.log import logger
from MRdataset.bids_utils import select_parameters


# TODO: check what if each variable is None. Apply try catch
class BIDSDataset(BaseDataset):
    """
    Container to manage the properties and methods of a BIDS dataset downloaded
    from OpenNeuro. It is a subclass of BaseDataset. Expects the data_source to
    contain JSON files for reading image acquisition parameters. Use
    include_nifti_header to extract parameter from nifti headers.
    """

    def __init__(self,
                 name=None,
                 data_source=None,
                 is_complete=True,
                 include_nifti_header=False,
                 **_kwargs):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_source : Path or str or List
            directory containing dicom files, supports nested hierarchies
        is_complete : bool
            whether the dataset is complete
        include_nifti_header :
            whether to check nifti headers for compliance,
            only used when --ds_format==bids
        Examples
        --------
        >>> from MRdataset.naive_bids import BIDSDataset
        >>> dataset = BIDSDataset()
        """

        super().__init__(data_source)
        self.is_complete = is_complete
        self.include_nifti_header = include_nifti_header
        self.name = name

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
        print('Started building BIDSLayout .. ')
        if isinstance(self.data_source, list):
            data_source = self.data_source[0]
        else:
            data_source = self.data_source

        bids_layout = BIDSLayout(data_source, validate=False)
        print('Completed BIDSLayout .. ')

        filters = self.get_filters()
        if not bids_layout.get(**filters):
            raise EOFError(f'No JSON files found at --data_source'
                           f' {data_source}')

        for datatype in VALID_DATATYPES:
            modality_obj = self.get_modality_by_name(datatype)
            if modality_obj is None:
                modality_obj = Modality(datatype)

            layout_subjects = bids_layout.get_subjects()
            if not layout_subjects:
                raise ValueError('No Subjects found in dataset')
            for n_sub in layout_subjects:
                subject_obj = modality_obj.get_subject_by_name(n_sub)
                if subject_obj is None:
                    subject_obj = Subject(n_sub)

                layout_sessions = bids_layout.get_sessions(subject=n_sub)

                if not layout_sessions:
                    logger.info('No sessions found. 1 is default '
                                'session name')
                    session_node = subject_obj.get_session_by_name('1')
                    if session_node is None:
                        session_node = Session('1')

                    filters = self.get_filters(subject=n_sub, datatype=datatype)
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
                    for n_sess in layout_sessions:
                        session_node = subject_obj.get_session_by_name(n_sess)
                        if session_node is None:
                            session_node = Session(n_sess)
                            filters = self.get_filters(subject=n_sub,
                                                       session=n_sess,
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
            raise EOFError('Expected Sidecar JSON files in --data_source.'
                           ' Got 0')

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
        parameters = {}
        for file in files:
            filename = file.filename
            parameters[filename] = {}
            params_from_file = select_parameters(file)
            parameters[filename].update(params_from_file)

        for filename, params in parameters.items():
            run_node = session_node.get_run_by_name(filename)
            if run_node is None:
                run_node = Run(filename)
            for k, v in parameters.items():
                run_node.params[k] = v
            run_node.echo_time = parameters.get('EchoTime', 1.0)
            session_node.add_run(run_node)
        return session_node
