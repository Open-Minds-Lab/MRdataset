"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
__version__ = '0.1.0'

import argparse
from MRdataset.data import find_dataset_using_style


def create_dataset(opt):
    """
    Create dataset as per arguments.

    This function acts as a Wrapper class for base.Dataset.
    This is the main interface between this package and your analysis

    Usage::

    >>> from MRdataset import create_dataset
    >>> dataset = create_dataset(opt)

    :param opt: expects either a Namespace object from argparse,
             for command-line interface or python dict
    :rtype: dataset container :class:`Dataset <MRdataset.data.base>`

    """
    if isinstance(opt, argparse.Namespace):
        opt = vars(opt)
    if isinstance(opt, dict):
        dataset_class = find_dataset_using_style(opt['style'])
        dataset = dataset_class(**opt)
        if opt.get('verbose', False):
            print(dataset)
    else:
        raise TypeError("Unsupported type. Expects either a Namespace or dict")
    return dataset
