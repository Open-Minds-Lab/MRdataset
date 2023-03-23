""" FastBIDSDataset class to manage BIDS datasets without BIDSLayout object"""
from pathlib import Path

from MRdataset.base import BaseDataset, Run, Modality, Subject, Session
from MRdataset.config import VALID_BIDS_EXTENSIONS, VALID_DATATYPES
from MRdataset.log import logger
from MRdataset.utils import select_parameters, files_in_path, get_ext


# TODO: check what if each variable is None. Apply try catch
class FastBIDSDataset(BaseDataset):
    """
    Container to manage the properties and methods of a BIDS dataset downloaded
    from OpenNeuro. In contrast to BIDSDataset, it doesn't create a BIDSLayout
    object for the dataset. Instead, it uses the file structure to extract
    information about the dataset. Therefore, it is much faster than
    BIDSDataset.
    """

    def __init__(self,
                 name=None,
                 data_source=None,
                 include_nifti_header=False,
                 is_complete=True,
                 **_kwargs):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_source : Path or str
            directory containing dicom files, supports nested hierarchies
        metadata_source : str or Path
            directory to store cache
        include_nifti_header :
            whether to check nifti headers for compliance,
            only used when --ds_format==bids
        Examples
        --------
        >>> from MRdataset.fastbids import FastBIDSDataset
        >>> dataset = FastBIDSDataset()
        """

        super().__init__(data_source)

        self.is_complete = is_complete
        self.include_nifti_header = include_nifti_header
        self.name = name

    def walk(self):
        """
        Retrieves filenames in the directory tree, verifies if it is json
        file, extracts relevant parameters and stores it in project. Creates
        a desirable hierarchy for a neuroimaging experiment
        """
        # TODO: Need to handle BIDS datasets without JSON files
        for file in files_in_path(self.data_source):
            ext = get_ext(file)
            if ext in VALID_BIDS_EXTENSIONS:
                self.read_single(file)
        if not self.modalities:
            raise ValueError('Expected Sidecar JSON files in '
                             '--data_source. Got 0 JSON files.')

    def read_single(self, file):
        datatype = file.parent.name
        if datatype not in VALID_DATATYPES:
            return
        modality_obj = self.get_modality_by_name(datatype)
        if modality_obj is None:
            modality_obj = Modality(datatype)
        n_sess = file.parents[1].name
        n_sub = file.parents[2].name
        if 'sub' in n_sess:
            logger.info('Sessions dont exist')
            n_sess = 'ses-01'
            n_sub = file.parents[1].name
        subject_obj = modality_obj.get_subject_by_name(n_sub)
        if subject_obj is None:
            subject_obj = Subject(n_sub)
        session_node = subject_obj.get_session_by_name(n_sess)
        if session_node is None:
            session_node = Session(n_sess)
        session_node = self.parse(session_node,
                                  file)
        if session_node.runs:
            subject_obj.add_session(session_node)
        if subject_obj.sessions:
            modality_obj.add_subject(subject_obj)
        if modality_obj.subjects:
            self.add_modality(modality_obj)
