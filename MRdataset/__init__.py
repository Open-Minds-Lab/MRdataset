"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
# __version__ = '0.1.0'


import logging

from MRdataset.logger import INFO_FORMATTER
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# defines the stream handler
_ch = logging.StreamHandler()  # creates the handler
_ch.setLevel(logging.INFO)  # sets the handler info
# sets the handler formatting
_ch.setFormatter(logging.Formatter(INFO_FORMATTER))
# adds the handler to the global variable: log
logger.addHandler(_ch)


from MRdataset.common import import_dataset, load_mr_dataset, save_mr_dataset
from MRdataset.utils import MRDS_EXT

from . import _version
__version__ = _version.get_versions()['version']
