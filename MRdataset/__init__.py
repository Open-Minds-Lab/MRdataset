"""Top-level package for MRdataset."""

__author__ = """Pradeep Raamana"""
__email__ = 'raamana@gmail.com'
__version__ = '0.1.0'

import argparse
from MRdataset.data import find_dataset_using_style

def create_dataset(opt):
    """
	Train a model to classify Foos and Bars.

	Usage::

	>>> import klassify
	>>> data = [("green", "foo"), ("orange", "bar")]
	>>> classifier = klassify.train(data)

	:param train_data: A list of tuples of the form ``(color, label)``.
	:rtype: A :class:`Classifier <Classifier>`

    Create dataset as per arguments.

    This function acts as a Wrapper class for base.Dataset.
    This is the main interface between this package and your analysis

    Args:
        opt: expects either a Namespace object from argparse,
             for command-line interface or python dict

    Examples:
        >>> from MRdataset import create_dataset
        >>> dataset = create_dataset(opt)
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
