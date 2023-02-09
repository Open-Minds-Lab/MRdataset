"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
# __version__ = '0.1.0'

from .common import import_dataset, load_mr_dataset, save_mr_dataset
from .utils import MRDS_EXT

from . import _version
__version__ = _version.get_versions()['version']
