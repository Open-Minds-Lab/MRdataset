""" FastBIDSDataset class to manage BIDS datasets without BIDSLayout object"""
from pathlib import Path

from MRdataset.base import BaseDataset, Modality, Subject, Session
from MRdataset.bids_utils import parse, is_valid_bidsfile, combine_entity_labels
from MRdataset.config import DatasetEmptyException
from MRdataset.log import logger
from MRdataset.utils import files_in_path


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
            if is_valid_bidsfile(file):
                self.read_single(file)
        if not self.modalities:
            raise DatasetEmptyException

    def read_single(self, filepath):
        datatype = filepath.parent.name
        n_sess = filepath.parents[1].name
        n_sub = filepath.parents[2].name
        if 'sub' in n_sess:
            logger.info('Sessions dont exist')
            n_sess = 'ses-01'
            n_sub = filepath.parents[1].name
        modality_name = combine_entity_labels(filepath.name, datatype)
        modality_obj = self.get_modality_by_name(modality_name)
        if modality_obj is None:
            modality_obj = Modality(modality_name)
        subject_obj = modality_obj.get_subject_by_name(n_sub)
        if subject_obj is None:
            subject_obj = Subject(n_sub)
        session_node = subject_obj.get_session_by_name(n_sess)
        if session_node is None:
            session_node = Session(n_sess)
        session_node = parse(session_node,
                             filepath)
        if session_node.runs:
            subject_obj.add_session(session_node)
        if subject_obj.sessions:
            modality_obj.add_subject(subject_obj)
        if modality_obj.subjects:
            self.add_modality(modality_obj)
