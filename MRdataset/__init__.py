"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
__version__ = '0.1.0'

from MRdataset.base import import_dataset

from . import _version
__version__ = _version.get_versions()['version']
