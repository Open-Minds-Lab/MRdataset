import logging
from functools import lru_cache
from pathlib import Path

# Constant Dicom Identifiers Used for dataset creation and manipulation
# TAGS = {
#     "series_instance_uid": (0x20, 0x0e),
#     "sequence": (0x18, 0x20),
#     "variant": (0x18, 0x21),
#     "patient_name": (0x10, 0x10),
#     "patient_id": (0x10, 0x20),
#     "study_id": (0x08, 0x1030),
#     "series_description": (0x08, 0x103E),
#     "series_number": (0x20, 0x11),
#     "protocol_name": (0x18, 0x1030),
#     "sequence_name": (0x18, 0x24),
#     "image_type": (0x08, 0x08),
#     "echo_number": (0x18, 0x86),
#     "te": [0x18, 0x81],
#     "patient_sex": [0x10, 0x40],
#     "patient_age": [0x10, 0x1010],
# }

# Constant Paths
# CACHE_DIR_NAME = ".mrdataset"
# CACHE_DIR = Path.home().resolve() / CACHE_DIR_NAME
# CACHE_DIR.mkdir(exist_ok=True)

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
