"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'

# __version__ = '0.1.0'
import logging
import sys

from MRdataset.config import configure_logger

logger = logging.getLogger(__name__)
logger = configure_logger(logger, output_dir=None, mode='w')

from MRdataset.common import import_dataset, load_mr_dataset, save_mr_dataset
from MRdataset.config import MRDS_EXT, DatasetEmptyException
from MRdataset.dicom_utils import is_dicom_file
from MRdataset.utils import valid_dirs
from MRdataset.base import BaseDataset
from MRdataset.bids import BidsDataset
from MRdataset.dicom import DicomDataset

try:
    from MRdataset._version import __version__
except ImportError:
    if sys.version_info < (3, 8):
        from importlib_metadata import version
    else:
        from importlib.metadata import version

    try:
        __version__ = version('MRdataset')
    except Exception:
        __version__ = "unknown"
