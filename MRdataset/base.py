import importlib
import warnings
from abc import ABC
from pathlib import Path
import pickle
from MRdataset.config import CACHE_DIR, setup_logger
from MRdataset.utils import random_name, timestamp
from typing import List, Optional, Type, Dict

# TODO:  include_phantom = False
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
    setup_logger('root', log_filename)

    dataset_class = find_dataset_using_style(style.lower())
    dataset = dataset_class(
        name=name,
        data_root=data_root,
        metadata_root=metadata_root,
        reindex=reindex,
    )
    if verbose:
        print(dataset)

    return dataset


def find_dataset_using_style(dataset_style: str):
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
                and issubclass(cls, Project):
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
    def __init__(self, name: str, **kwargs) -> None:
        self.name = name
        self._children = list()
        self._compliant_children = list()
        self._non_compliant_children = list()

    def __add__(self, other: "Node") -> None:
        # TODO: improve logic , better dictionary
        for child in self._children:
            if child.name == other.name:
                return
        self._children.append(other)

    def _get(self, name: str) -> Optional[Type["Node"]]:
        for child in self._children:
            if child.name == name:
                return child
        else:
            return None

    def _add_compliant_name(self, other: str) -> None:
        for name in self._compliant_children:
            if name == other:
                return
        self._compliant_children.append(other)

    def _add_non_compliant_name(self, other: str) -> None:
        for name in self._non_compliant_children:
            if name == other:
                return
        self._non_compliant_children.append(other)

    def __repr__(self) -> str:
        return self.__str__()


class Project(Node):
    """
            Container to manage properties and issues at the project level.
        Encapsulates all the details necessary for a complete project.
        A single project may contain multiple modalities, and each modality
        will have atleast single subject.
    """
    def __init__(self, name, data_root, metadata_root, **kwargs):
        super().__init__(name)
        # Manage directories
        self.data_root = Path(data_root)
        if not self.data_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.metadata_root = Path(metadata_root)
        if not self.metadata_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        self.cache_path = None

    @property
    def modalities(self) -> List["Modality"]:
        return self._children

    @property
    def compliant_modality_names(self) -> List[str]:
        return self._compliant_children

    @property
    def non_compliant_modality_names(self) -> List[str]:
        return self._non_compliant_children

    def add_modality(self, new_modality: "Modality") -> None:
        self.__add__(new_modality)

    def get_modality(self, name: str) -> Optional["Modality"]:
        return self._get(name)

    def add_compliant_modality_name(self, modality_name: str) -> None:
        self._add_compliant_name(modality_name)

    def add_non_compliant_modality_name(self, modality_name: str) -> None:
        self._add_non_compliant_name(modality_name)

    def save_dataset(self) -> None:
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load_dataset(self) -> None:
        with open(self.cache_path, 'rb') as f:
            temp_dict = pickle.load(f)
            self.__dict__.update(temp_dict)


class Modality(Node):
    """
    Container to manage properties and issues at the modality level.
    Encapsulates all the details necessary for a modality.
    A single modality may contain multiple subjects, and each subject
    will have atleast single session.
    """
    def __init__(self, name):
        super().__init__(name)
        self.reference = dict()
        # multi_echo is not set
        self.multi_echo_flag = None
        self.compliant = None

    def get_reference(self, echo_number) -> Dict:
        return self.reference[echo_number]

    @property
    def subjects(self) -> List["Subject"]:
        return self._children

    @property
    def compliant_subject_names(self) -> List[str]:
        return self._compliant_children

    @property
    def non_compliant_subject_names(self) -> List[str]:
        return self._non_compliant_children

    def add_subject(self, new_subject) -> None:
        if not isinstance(new_subject, Subject):
            raise TypeError("Expected argument of type <Subject>, got {} instead".format(type(new_subject)))
        self.__add__(new_subject)

    def add_compliant_subject_name(self, subject_name: str) -> None:
        self._add_compliant_name(subject_name)

    def add_non_compliant_subject_name(self, subject_name) -> None:
        self._add_non_compliant_name(subject_name)

    def get_subject(self, name) -> Optional["Subject"]:
        return self._get(name)

    def __str__(self) -> str:
        return "Modality {} with {} subjects".format(self.name, len(self.subjects))

    def set_reference(self, params: Dict, echo) -> None:
        self.reference[echo] = params.copy()

    # TODO : Check if function is even required, else delete
    def is_multi_echo(self):
        return len(self.reference) > 1


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
    def sessions(self) -> List["Session"]:
        return self._children

    def add_session(self, new_session) -> None:
        if not isinstance(new_session, Session):
            raise TypeError("Expected argument of type <Session>, got {} instead"
                            "".format(type(new_session)))
        self.__add__(new_session)

    def get_session(self, name) -> Optional["Session"]:
        return self._get(name)

    def __str__(self) -> str:
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
    #
    # def is_multi_echo(self):
    #     return len(self.runs) > 1


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
