from abc import ABC, abstractmethod
import argparse
import importlib


class Dataset(ABC):
    """This class is an abstract base class (ABC) for datasets.

    To create a subclass, you need to implement the following functions:
    -- <__init__>:      initialize the class, first call super().__init__()
    -- <__getitem__>:   get a data sample
    """
    def __init__(self, **kwargs):
        """
        Initialize the class; save the options in the class
        """
        self.name = None

    @abstractmethod
    def __getitem__(self, *args, **kwargs):
        raise NotImplementedError("__getitem__ attribute implementation for dataset is missing.")

    @abstractmethod
    def __len__(self):
        raise TypeError("__len__ attribute implementation for dataset is missing.")


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
        if opt.get('verbose', True):
            print(dataset)
    else:
        raise TypeError("Unsupported type. Expects either a Namespace or dict")
    return dataset


def find_dataset_using_style(dataset_style):
    """
    Import the module "data/{style}_dataset.py", which will instantiate
    {Style}Dataset(). For future, please ensure that any {Style}Dataset
    is a subclass of MRdataset.base.Dataset
    """

    dataset_modulename = "MRdataset.data." + dataset_style + "_dataset"
    datasetlib = importlib.import_module(dataset_modulename)

    dataset = None
    target_dataset_class = dataset_style+'dataset'
    for name, cls in datasetlib.__dict__.items():
        if name.lower() == target_dataset_class.lower() \
                and issubclass(cls, Dataset):
            dataset = cls

    if dataset is None:
        raise NotImplementedError("Expected to find %s which is supposed  \
        to be a subclass of base.Dataset in %s.py" % (target_dataset_class, dataset_modulename))

    return dataset




