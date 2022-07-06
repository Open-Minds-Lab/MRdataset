import importlib
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from collections import defaultdict


import MRdataset


def create_dataset(data_root=None, style='xnat', name=None, reindex=False, verbose=False):
    """
    Create dataset as per arguments.

    This function acts as a Wrapper class for base.Dataset.
    This is the main interface between this package and your analysis

    Usage::

    >>> from MRdataset import create_dataset
    >>> data = create_dataset('xnat', '/path/to/my/data/')

    :param style: expects a string specifying the Dataset class.
            Imports "data/{style}_dataset.py
    :param data_root: /path/to/my/dataset containing .dcm files
    :param name: optional identifier you may want to use,
            otherwise it uses project name from dicom properties
    :param reindex: optional flag, if true delete all associated metadata files and rebuilds index
    :param verbose: print more stuff
    :rtype: dataset container :class:`Dataset <MRdataset.data.base>`

    """
    if not Path(data_root).is_dir():
        raise OSError('Expected valid directory for --data_root argument, Got {0}'.format(data_root))
    data_root = Path(data_root).resolve()

    metadata_root = data_root / CACHE_DIR
    metadata_root.mkdir(exist_ok=True)
    if name is None:
        warnings.warn('Expected a unique identifier for caching data. Got NoneType. '
                      'Using a random name. Use --name flag for persistent metadata',
                      stacklevel=2)
        name = functional.random_name()

    dataset_class = find_dataset_using_style(style.lower())
    dataset = dataset_class(data_root=data_root,
                            metadata_root=metadata_root,
                            name=name,
                            reindex=reindex,
                            verbose=verbose)
    if verbose:
        print(dataset)

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


class Dataset(ABC):
    """This class is an abstract base class (ABC) for datasets.

    To create a subclass, you need to implement the following functions:
    -- <__init__>:      initialize the class, first call super().__init__()
    -- <__getitem__>:   get a data sample
    """
    def __init__(self, **kwargs):
        """
        Initialize the class; save the options in the classk
        """
        self.data_root = None
        self.metadata_root = None

    @abstractmethod
    def __getitem__(self, *args, **kwargs):
        raise NotImplementedError("__getitem__ attribute implementation for dataset is missing.")

    @abstractmethod
    def __len__(self):
        raise TypeError("__len__ attribute implementation for dataset is missing.")



class Node(ABC):
    """
    An abstract class specifying a generic node in a neuroimaging experiment.
    It is inherited to create subclasses like ProjectNode, ModalityNode, SubjectNode etc.
    """
    def __init__(self, name):
        self.name = name
        self.error = False
        self.params = dict()
        self._children = list()

    def __add__(self, other):
        for child in self._children:
            if child.name == other.name:
                return
        self._children.append(child)

    def _get(self, name):
        for child in self._children:
            if child.name == name:
                return child
        else:
            return None

    def param_difference(self, other, ignore_params):
        if isinstance(other, Node):
            other = other.params
        elif isinstance(other, dict):
            return list(dict_diff(self.params, other), ignore=set(ignore_params))
        else:
            raise TypeError("Expected type 'dict', got {} instead".format(type(other)))

    def __repr__(self):
        return self.__str__()


class Project(Node):
    """
    Container to manage properties and issues at the project level.
    Encapsulates all the details necessary for a complete project.
    A single project may contain multiple modalities, and each modality
    will have atleast single subject.
    """
    def __init__(self, name):
        super().__init__(name)

    @property
    def modalities(self):
        return self._children

    def add_modality(self, new_modality):
        self.add(new_modality)

    def get_modality(self, name):
        return self._get(name)

    def __str__(self):
        return "Project {} with {} modalities".format(self.name, len(self.modalities))



class Modality(Node):
    """
    Container to manage properties and issues at the modality level.
    Encapsulates all the details necessary for a modality.
    A single modality may contain multiple subjects, and each subject
    will have atleast single session.
    """
    def __init__(self, name):
        super().__init__(name)
        self.subjects = list()

    @property
    def subjects(self):
        return self._children

    def add_subject(self, new_subject):
        self.add(new_subject)

    def get_subject(self, name):
        return self._get(name)

    def __str__(self):
        return "Modality {} with {} subjects".format(self.name, len(self.subjects))


class Subject(Node):
    """
    Container to manage properties and issues at the subject level.
    Encapsulates all the details necessary for a subject.
    A single subject may contain multiple sessions for a single modality.
    For example, For a project called ABCD, it is grouped by modalities like T1, T2 etc.
    So, each modality, say T1 will have multiple subjects. And each subject
    can have multiple run instances where a run instance is a series of brain volumes
    """
    def __init__(self, name, path):
        super().__init__(name)
        self.path = Path(path).resolve()
        if not self.path.exists():
            raise FileNotFoundError('Provide a valid /path/to/subject/')
        self.run_instances = list()

    @property
    def run_instances(self):
        return self._children

    def add_run_instance(self, new_run_instance):
        self.add(new_run_instance)

    def get_run_instance(self, name):
        return self._get(name)


    def __str__(self):
        return "Subject {} with {} run instances".format(self.name, len(self.run_instances))


class RunInstance():
    """
    Container to manage properties and issues at the run level.
    Encapsulates all the details necessary for a run instance.
    A run instance is a series of brain volumes.
    This is the lowest level in the hierarchy. Individual .dcm files should have same
    parameters at this level.
    """
    def __init__(self, name):
        self.name = name
        self.error = False
        self.params = dict()
        self.files = list()

    def __str__(self):
        return "Run {}".format(self.name)

# class Slice(Node):
#     def __init__(self, name, filepath):
#         super.__init__(name)
#         self.path = filepath
#
#     def parse_params(self):
#         from common import parse
#         self.params = parse(self.path)
#
#     def __str__(self):
#         return "Slice {}".format(self.name)
