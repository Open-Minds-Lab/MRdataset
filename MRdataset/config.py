import logging
import tempfile
from pathlib import Path

from protocol.config import ACRONYMS_IMAGING_PARAMETERS

#: Parameters that are supported by MRdataset
VALID_PARAMETERS = sorted(list(ACRONYMS_IMAGING_PARAMETERS.keys()))

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


def configure_logger(log, output_dir, mode='w', level='ERROR'):
    """
    Initiate log files.

    Parameters
    ----------
    log : logging.Logger
        The logger object.
    mode : str, (``'w'``, ``'a'``)
        The writing mode to the log files.
        Defaults to ``'w'``, overwrites previous files.    """
    console_handler = logging.StreamHandler()  # creates the handler
    warn_formatter = '%(filename)s:%(name)s:%(funcName)s:%(lineno)d: %(message)s'
    error_formatter = '%(asctime)s - %(levelname)s - %(message)s'
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    output_dir = Path(output_dir) / '.mrdataset'
    output_dir.mkdir(parents=True, exist_ok=True)

    warn_file = output_dir / 'warn.log'
    if level == 'WARNING':
        warn = logging.FileHandler(warn_file, mode=mode)
        warn.setLevel(logging.WARN)
        warn.setFormatter(logging.Formatter(warn_formatter))
        log.addHandler(warn)

    # keep only errors on console
    console_handler.setLevel(logging.ERROR)  # sets the handler info
    console_handler.setFormatter(logging.Formatter(error_formatter))
    log.addHandler(console_handler)

    error_file = output_dir / 'error.log'
    error = logging.FileHandler(error_file, mode=mode)
    error.setLevel(logging.ERROR)
    error.setFormatter(logging.Formatter(error_formatter))
    log.addHandler(error)
    return log
