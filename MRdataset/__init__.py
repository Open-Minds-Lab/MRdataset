"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'

# __version__ = '0.1.0'
import logging

from MRdataset.config import configure_logger

logger = logging.getLogger(__name__)
logger = configure_logger(logger, output_dir=None, mode='w')

from MRdataset.common import import_dataset, load_mr_dataset, save_mr_dataset
from MRdataset.config import MRDS_EXT, DatasetEmptyException
from MRdataset.dicom_utils import is_dicom_file
from MRdataset.utils import valid_dirs
from MRdataset.base import BaseDataset
from MRdataset.dicom import DicomDataset

try:
    from MRdataset._version import __version__
except ImportError:
    raise ImportError('It seems MRdataset is not installed correctly. Use pip '
                      ' to install it first.')
