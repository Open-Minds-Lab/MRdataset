import importlib
import warnings
from abc import ABC
from pathlib import Path

from MRdataset.config import CACHE_DIR, setup_logger
from MRdataset.utils import random_name, timestamp


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
        name = random_name()

    log_filename = metadata_root / '{}_{}.log'.format(name, timestamp())
    logger = setup_logger('root', log_filename)

    dataset_class = find_dataset_using_style(style.lower())
    dataset = dataset_class(
        name=name,
        data_root=data_root,
        metadata_root=metadata_root,
        reindex=reindex,
        verbose=verbose
    )
    if verbose:
        print(dataset)

    return dataset


def find_dataset_using_style(dataset_style):
    """
    Import the module "data/{style}_dataset.py", which will instantiate
    {Style}Dataset(). For future, please ensure that any {Style}Dataset
    is a subclass of MRdataset.base.Dataset
    """

    dataset_modulename = "MRdataset." + dataset_style + "_dataset"
    datasetlib = importlib.import_module(dataset_modulename)

    dataset = None
    target_dataset_class = dataset_style+'dataset'
    for name, cls in datasetlib.__dict__.items():
        if name.lower() == target_dataset_class.lower() \
                and issubclass(cls, Node):
            dataset = cls

    if dataset is None:
        raise NotImplementedError("Expected to find %s which is supposed  \
        to be a subclass of base.Node in %s.py" % (target_dataset_class, dataset_modulename))
    return dataset


class Node(ABC):
    """
    An abstract class specifying a generic node in a neuroimaging experiment.
    It is inherited to create subclasses like ProjectNode, ModalityNode, SubjectNode etc.
    """
    def __init__(self, name, **kwargs):
        self.name = name
        self._children = list()
        self._compliant_children = list()
        self._non_compliant_children = list()

    def __add__(self, other):
        for child in self._children:
            if child.name == other.name:
                return
        self._children.append(other)

    def _get(self, name):
        for child in self._children:
            if child.name == name:
                return child
        else:
            return None

    def _add_compliant(self, other):
        for child in self._compliant_children:
            if child == other:
                return
        self._compliant_children.append(other)

    def _add_non_compliant(self, other):
        for child in self._compliant_children:
            if child == other:
                return
        self._non_compliant_children.append(other)

    def __repr__(self):
        return self.__str__()


class Modality(Node):
    """
    Container to manage properties and issues at the modality level.
    Encapsulates all the details necessary for a modality.
    A single modality may contain multiple subjects, and each subject
    will have atleast single session.
    """
    def __init__(self, name):
        super().__init__(name)
        self._reference = dict()
        # multi_echo is not set
        self.multi_echo_flag = None
        self.compliant = None

    def get_reference(self, echo_number):
        return self._reference[echo_number]

    @property
    def subjects(self):
        return self._children

    @property
    def compliant_subjects(self):
        return self._compliant_children

    @property
    def non_compliant_subjects(self):
        return self._non_compliant_children

    def add_subject(self, new_subject):
        if not isinstance(new_subject, Subject):
            raise TypeError("Expected argument of type <Subject>, got {} instead".format(type(new_subject)))
        self.__add__(new_subject)

    def add_compliant_subject(self, subject_name):
        self._add_compliant(subject_name)

    def add_non_compliant_subject(self, subject_name):
        self._add_non_compliant(subject_name)

    def get_subject(self, name):
        return self._get(name)

    def __str__(self):
        return "Modality {} with {} subjects".format(self.name, len(self.subjects))

    def set_reference(self, params, echo):
        self._reference[echo] = params.copy()

    def is_multi_echo(self):
        if self.is_multi_echo() is None:
            for subject in self.subjects:
                for session in subject.sessions:
                    if session.is_multi_echo():
                        self.multi_echo_flag = True
                        return self.multi_echo_flag
            self.multi_echo_flag = False
        return self.multi_echo_flag


class Subject(Node):
    """
    Container to manage properties and issues at the subject level.
    Encapsulates all the details necessary for a subject.
    A single subject may contain multiple sessions for a single modality.
    For example, For a project called ABCD, it is grouped by modalities like T1, T2 etc.
    So, each modality, say T1 will have multiple subjects. And each subject
    can have multiple sessions.
    """
    def __init__(self, name):
        super().__init__(name)
        self.compliant = None

    @property
    def sessions(self):
        return self._children

    @property
    def compliant_sessions(self):
        return self._compliant_children

    @property
    def non_compliant_sessions(self):
        return self._non_compliant_children

    def add_session(self, new_session):
        if not isinstance(new_session, Session):
            raise TypeError("Expected argument of type <Session>, got {} instead".format(type(new_session)))
        self.__add__(new_session)

    def get_session(self, name):
        return self._get(name)

    def add_compliant_session(self, session_name):
        self._add_compliant(session_name)

    def add_non_compliant_session(self, session_name):
        self._add_non_compliant(session_name)

    def __str__(self):
        return "Subject {} with {} sessions".format(self.name, len(self.sessions))


class Session(Node):
    """
    Container to manage properties and issues at the session level.
    Encapsulates all the details necessary for a session.
    A single session may contain multiple sessions for a single modality.
    For example, For a project called ABCD, it is grouped by modalities like T1, T2 etc.
    So, each modality, say T1 will have multiple sessions. And each session
    can have multiple run where a run instance is a series of brain volumes
    """
    def __init__(self, name, path):
        super().__init__(name)
        self.params = dict()
        self.path = Path(path).resolve()
        self.compliant = None
        if not self.path.exists():
            raise FileNotFoundError('Provide a valid /path/to/session/')

    @property
    def runs(self):
        return self._children

    def add_run(self, new_run):
        if not isinstance(new_run, Run):
            raise TypeError("Expected argument of type <Run>, got {} instead".format(type(new_run)))
        self.__add__(new_run)

    def get_run(self, name):
        return self._get(name)

    def __str__(self):
        return "Session {} with {} runs".format(self.name, len(self.runs))

    def is_multi_echo(self):
        return len(self.runs) > 1


class Run(Node):
    """
    Container to manage properties and issues at the run level.
    Encapsulates all the details necessary for a run.
    A run is a series of brain volumes.
    This is the lowest level in the hierarchy. Individual .dcm files should have same
    parameters at this level.
    """
    def __init__(self, name):
        super().__init__(name)
        self.echo_time = 0
        self.error = False
        self.params = dict()
        self.delta = None

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
