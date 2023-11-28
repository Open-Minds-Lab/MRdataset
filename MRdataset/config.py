import logging
import tempfile
from pathlib import Path

from protocol import ACRONYMS_IMAGING_PARAMETERS

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


def configure_logger(log, output_dir, mode='w', level='WARNING'):
    """
    Initiate log files.

    Parameters
    ----------
    log : logging.Logger
        The logger object.
    mode : str, (``'w'``, ``'a'``)
        The writing mode to the log files.
        Defaults to ``'w'``, overwrites previous files.
    output_dir : str or Path
        The path to the output directory.
    level : str,
        The level of logging to the console. One of ['WARNING', 'ERROR']
    """

    console_handler = logging.StreamHandler()  # creates the handler
    warn_formatter = ('%(filename)s:%(name)s:%(funcName)s:%(lineno)d:'
                      ' %(message)s')
    error_formatter = '%(asctime)s - %(levelname)s - %(message)s'
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    output_dir = Path(output_dir) / '.mrdataset'
    output_dir.mkdir(parents=True, exist_ok=True)

    options = {
        "warn": {
            'level': logging.WARN,
            'file': output_dir / 'warn.log',
            'formatter': warn_formatter
        },
        "error": {
            'level': logging.ERROR,
            'file': output_dir / 'error.log',
            'formatter': error_formatter
        }
    }

    if level == 'ERROR':
        config = options['error']
    else:
        config = options['warn']

    file_handler = logging.FileHandler(config['file'], mode=mode)
    file_handler.setLevel(config['level'])
    file_handler.setFormatter(logging.Formatter(config['formatter']))
    log.addHandler(file_handler)

    console_handler.setLevel(config['level'])  # sets the handler info
    console_handler.setFormatter(logging.Formatter(config['formatter']))
    log.addHandler(console_handler)
    return log


def previous_log_fpath(folder, name):
    """
    Return the path to the previous run log file
    """
    return Path(folder) / f'{name}_previous_run_log.json'
