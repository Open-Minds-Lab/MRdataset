"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
# __version__ = '0.1.0'


import logging

from MRdataset.logger import INFO_FORMATTER, init_log_files
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# defines the stream handler
_ch = logging.StreamHandler()  # creates the handler
_ch.setLevel(logging.INFO)  # sets the handler info
# sets the handler formatting
_ch.setFormatter(logging.Formatter(INFO_FORMATTER))
# adds the handler to the global variable: log
logger.addHandler(_ch)
init_log_files(logger, mode='w')


from MRdataset.common import import_dataset, load_mr_dataset, save_mr_dataset
from MRdataset.config import MRDS_EXT, DatasetEmptyException
from MRdataset.dicom_utils import is_dicom_file
from MRdataset.utils import valid_dirs
from MRdataset.base import BaseDataset

from . import _version
__version__ = _version.get_versions()['version']
