from abc import ABC, abstractmethod
from collections import UserDict
from pathlib import Path

from protocol import ImagingSequence
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from MRdataset.utils import files_in_folders, folders_with_min_files
from MRdataset.dicom_utils import (is_valid_inclusion, get_metadata,
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
# https://github.com/icometrix/dicom2nifti/blob/ecbf43a66174375285fae485439ea8dd940005ba/dicom2nifti/convert_dir.py#L68
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
        self.pattern = "*.dcm"
        self.min_count = 3  # min slice count to be considered a volume


    def traverse(self):
        """default method to traverse the dataset"""

        sub_folders = folders_with_min_files(self.root, self.pattern, self.min_count)

        for folder in sub_folders:

            # within a folder, a volume can be multi-echo

            dcm_files = list(folder.glob(self.pattern))

            # run some basic validation of these dcm slice collection
            #   SeriesInstanceUID must match
            #   parameter values must match, except echo time
            first_slice = ImagingSequence(dicom=dcm_files[0],
                                          name='first')
            non_compl = list()
            for dcm in dcm_files[1:]:
                cur_slice = ImagingSequence(dicom=dcm, name='current')
                if not cur_slice == first_slice:
                    non_compl.append(cur_slice)

            for dcm_path in dcm_files:

                try:
                    dicom = dcmread(dcm_path, stop_before_pixels=True)
                except InvalidDicomError as ide:
                    print(f'Invalid DICOM file at {dcm_path}')
                    continue

                if not is_valid_inclusion(dcm_path, dicom, self.include_phantoms):
                    continue

            seq_name, subject_id, session_id, run_name = get_metadata(dicom)

            if idx == 0:
                first_slice = ImagingSequence(dicom=dicom, name=f'First.{seq_name}')
            else:
                cur_slice = ImagingSequence(dicom=dicom, name=f'Current.{seq_name}')

                if not cur_slice == first_slice:  # noqa
                    non_compl.append(cur_slice)

        first_slice.multi_echo = False
        if len(non_compl) > 1:
            echo_times = set()
            echo_times.add(first_slice['EchoTime'].value)
            for ncs in non_compl:
                echo_times.add(ncs['EchoTime'].value)
            if len(echo_times) > 1:
                first_slice.multi_echo = True

        return seq_name, first_slice, subject_id, session_id, run_name  # noqa
