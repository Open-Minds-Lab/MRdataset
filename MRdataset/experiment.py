from abc import ABC, abstractmethod
from collections import UserDict
from pathlib import Path

from protocol import ImagingSequence
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from MRdataset.utils import files_in_folders
from MRdataset.dicom_utils import (is_valid_inclusion,
                                   get_dicom_modality_tag, get_run_id,
                                   parse_imaging_params)
from MRdataset.dicom_utils import get_sequence
from MRdataset.config import TAGS


# A dataset is a collection of subjects
# A subject is a collection of sessions
# A session is a collection of runs
# A run is one instance of a sequence;
# A sequence is a collection of parameters
#
# related useful references
#   https://bids-specification.readthedocs.io/en/stable/appendices/entities.html
#
# dicom2nifti logic for naming files:
# https://github.com/icometrix/dicom2nifti/blob
# /ecbf43a66174375285fae485439ea8dd940005ba/dicom2nifti/convert_dir.py#L68
#

class Run(UserDict):
    """Container for an imaging run.

    Design:
    - A run is an instance of a sequence
    - A session can have multiple runs acquired with the same sequence/parameters
    - for only a SINGLE subject

    """


    def __init__(self,
                 session_id: str = 'SessionID',
                 subject_id: str = 'SubjectID',
                 sequence: ImagingSequence = None):
        """constructor"""

        super().__init__()
        self.session_id = session_id
        self.subject_id = subject_id
        self.sequence = sequence


class Session(UserDict):
    """Container for an imaging session.

    Design:
    - A session is a collection of runs,
        and each run is different acquisition with the same sequence/parameters
    - for only a SINGLE subject
    - like a Visit in longitudinal studies
    """


    def __init__(self,
                 session_id='SessionID',
                 subject_id='SubjectID',
                 runs : list[Run] = None):
        """constructor"""

        super().__init__()
        self.session_id = session_id
        self.subject_id = subject_id
        self.runs = runs


class Subject(UserDict):
    """base class for all subjects"""


    def __init__(self,
                 subject_id='SubjectID',
                 sessions : list[Session] = None):
        """constructor"""

        super().__init__()
        self.subject_id = subject_id
        self.sessions = sessions


class BaseDataset(ABC):
    """base class for all MR datasets"""


    def __init__(self,
                 root,
                 name: str = 'Dataset',
                 format: str = 'DICOM',
                 subjects : list[Subject] = None):
        """constructor"""

        fp = Path(root).resolve()
        if fp.exists():
            self.root = fp
        else:
            raise IOError('Root folder for {} does not exist at {}'
                          ''.format(name, fp))

        self.name = name
        self.format = format
        self.subjects = subjects


    @abstractmethod
    def traverse(self):
        """default method to traverse the dataset"""


    def add(self, dcm):
        """adds a given subject, session or run to the dataset"""


class DicomDataset(BaseDataset, ABC):
    """Class to represent a DICOM dataset"""


    def __init__(self,
                 root,
                 name='DicomDataset',
                 include_phantoms=False):
        """constructor"""

        super().__init__(root=root, name=name, format='DICOM')

        self.include_phantoms = include_phantoms


    def traverse(self):
        """default method to traverse the dataset"""

        for dcm_path in files_in_folders([self.root, ]):

            try:
                dicom = dcmread(dcm_path, stop_before_pixels=True)
            except InvalidDicomError as ide:
                print(f'Invalid DICOM file at {dcm_path}')
                continue

            if not is_valid_inclusion(dcm_path, dicom, self.include_phantoms):
                continue

            #   name: SeriesNumber_Suffix
            #   priority for suffix: SeriesDescription, SequenceName, ProtocolName
            seq_name = get_sequence(dicom)
            print(f'{seq_name}')

            patient_id = str(dicom.get('PatientID', None))

            # series number is a proxy for session?
            series_num = str(dicom.get('SeriesNumber', None))

            run_name = dicom.get('SeriesInstanceUID', None)  # get_run_id(dicom)

            params = parse_imaging_params(dicom)
            print()
