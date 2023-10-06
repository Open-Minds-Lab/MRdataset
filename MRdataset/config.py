MRDS_EXT = '.mrds.pkl'
VALID_DATASET_FORMATS = [
    'dicom',
    'bids',
]

VALID_BIDS_EXTENSIONS = ['.json', '.nii', '.nii.gz']


VALID_DATATYPES = [
    'anat',
    'beh',
    'dwi',
    'eeg',
    'fmap',
    'func',
    'ieeg',
    'meg',
    'micr',
    'perf',
    'pet'
]


# Suppress duplicated warnings

class MRException(Exception):
    """
    Custom error that is raised when some critical properties are not found
    in dicom file
    """

    def __init__(self, message, **kwargs):
        super().__init__(message)


class MRdatasetWarning(Exception):
    """
    Custom error that is raised when some critical properties are not found
    in dicom file
    """

    def __init__(self, message, **kwargs):
        super().__init__(message)


class DatasetEmptyException(MRException):
    def __init__(self):
        super().__init__('Expected Sidecar DICOM/JSON files in '
                         '--data_source. Got 0 DICOM/JSON files.')
