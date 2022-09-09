import importlib
import warnings
from pathlib import Path
import pickle
from MRdataset.config import CACHE_DIR, setup_logger
from MRdataset.utils import random_name, timestamp
from typing import List, Optional, Type
import pandas as pd


def import_dataset(data_root=None,
                   style='xnat',
                   name=None,
                   reindex=False,
                   include_phantom=False,
                   verbose=False,
                   metadata_root=None) -> "Project":
    """
    Create dataset as per arguments. This function acts as a Wrapper class for
    base.Dataset. This is the main interface between this package and your
    analysis.

    Parameters
    ----------
    data_root : str
        path/to/my/dataset containing .dcm files
    style : str
        Specify dataset type. Imports the module "{style}_dataset.py",
        which will instantiate {Style}Dataset().
    name : str
        Identifier for the dataset, like ADNI. The name used to save cached
        results
    reindex : bool
        Similar to --no-cache. Rejects all cached files and rebuilds index.
    include_phantom
        Whether to include non-subject scans like localizer, acr/phantom,
        aahead_scout
    verbose :
        The flag allows you to change the verbosity of execution
    metadata_root :
        change the default cache directory
    Returns
    -------
    dataset : MRdataset.base.Project()
        dataset container class

    Examples
    --------
    >>> from MRdataset import import_dataset
    >>> data = import_dataset('xnat', '/path/to/my/data/')
    """

    if not Path(data_root).is_dir():
        raise OSError('Expected valid directory for --data_root argument,'
                      ' Got {0}'.format(data_root))
    data_root = Path(data_root).resolve()

    if not metadata_root:
        metadata_root = Path.home() / CACHE_DIR
        metadata_root.mkdir(exist_ok=True)

    if not Path(metadata_root).is_dir():
        raise OSError('Expected valid directory for --metadata_root argument,'
                      ' Got {0}'.format(metadata_root))
    metadata_root = Path(metadata_root).resolve()

    if name is None:
        warnings.warn(
            'Expected a unique identifier for caching data. Got NoneType. '
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
        include_phantom=include_phantom,
        reindex=reindex,
    )
    if verbose:
        print(dataset)

    return dataset


def find_dataset_using_style(dataset_style: str):
    """
    Imports the module "{style}_dataset.py", which will instantiate
    {Style}Dataset(). For future, please ensure that any {Style}Dataset
    is a subclass of MRdataset.base.Dataset

    Parameters
    ----------
    dataset_style : str
        Specify the type of dataset

    Returns
    -------
    dataset: MRdataset.base.Project()
        dataset container class
    """
    dataset_modulename = "MRdataset.{}_dataset".format(dataset_style)
    dataset_lib = importlib.import_module(dataset_modulename)

    dataset = None
    target_dataset_class = '{}dataset'.format(dataset_style)
    for name, cls in dataset_lib.__dict__.items():
        name_matched = name.lower() == target_dataset_class.lower()
        if name_matched and issubclass(cls, Project):
            dataset = cls

    if dataset is None:
        raise NotImplementedError(
            "Expected %s to be a subclass of MRdataset.base.Project in % s.py."
            % (target_dataset_class, dataset_modulename))
    return dataset


class Node:
    """
    An abstract class specifying a generic node in a neuroimaging experiment.
    It is inherited to create subclasses like Project, Modality, Subject etc.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    """

    def __init__(self, name: str, **kwargs) -> None:
        """
        Constructor

        Parameters
        ----------
        name : str
            identifier for instance. For example : name or id
        kwargs : dict
            Additional keyword arguments passed to Node
        """
        self.name = name
        self._children = dict()
        self._compliant_children = list()
        self._non_compliant_children = list()

    @property
    def children(self):
        """
        Each node can be connected to several children, generally
        subcomponents of Node
        """
        return list(self._children.values())

    def add(self, other: "Node") -> None:
        """
        Adds a child node to self._children dict, if already present
        updates it

        Parameters
        ----------
        other : Node
            another Node object that must be added to list of children
        """
        if not isinstance(other, Node):
            raise TypeError("must be base.Node, not {}".format(type(other)))
        self._children[other.name] = other

    def _get(self, name: str) -> Optional[Type["Node"]]:
        """
        Fetches a child node which has the same key as "name". If key is not
        available, returns None

        Parameters
        ----------
        name : str
            Key/Identifier to be searched in the dictionary

        Returns
        -------
        None or Node
            value specified for key if key is in self._children
        """
        return self._children.get(name, None)

    def _add_compliant_name(self, other: str) -> None:
        """
        Add a name to list of compliant children
        Parameters
        ----------
        other : str
            Name to be added to list of compliant children
        """
        if not isinstance(other, str):
            raise TypeError('must be str, not {} '.format(type(other)))
        if other in self._compliant_children:
            return
        self._compliant_children.append(other)

    def _add_non_compliant_name(self, other: str) -> None:
        """
        Add a name to list of non-compliant children
        Parameters
        ----------
        other : str
            Name to be added to list of non-compliant children
        """
        if not isinstance(other, str):
            raise TypeError('must be str, not {}'.format(type(other)))
        if other in self._non_compliant_children:
            return
        self._non_compliant_children.append(other)

    def __repr__(self) -> str:
        return "<class MRdataset.base.{}({})>".format(self.__class__.__name__,
                                                      self.name)

    def __str__(self):
        if len(self.children) > 0:
            return "{} {} with {} {}".format(
                self.__class__.__name__,
                self.name,
                len(self.children),
                self.children[0].__class__.__name__)
        else:
            return "{} {}".format(self.__class__.__name__, self.name)


class Project(Node):
    """
    Container to manage properties and issues at the project level.
    Encapsulates all the details necessary for a complete project.
    A single project may contain multiple modalities, and each modality
    will have atleast single subject.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    data_root : str or Path
        directory containing dataset with dicom files
    metadata_root : str or Path
        directory to store cache
    """

    def __init__(self, name, data_root, metadata_root, **kwargs):
        """
        Constructor

        Parameters
        ----------
        name : str
            Identifier/name for the node
        data_root : str or Path
            directory containing dataset with dicom files
        metadata_root : str or Path
            directory to store cache
        kwargs : dict
            Additional keyword arguments passed to Project
        """
        super().__init__(name)
        # Manage directories
        self.data_root = Path(data_root)
        if not self.data_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.metadata_root = Path(metadata_root)
        if not self.metadata_root.exists():
            self.metadata_root.mkdir(exist_ok=True)
            # raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        self.cache_path = self.metadata_root / "{}.pkl".format(self.name)

    @property
    def modalities(self) -> List["Modality"]:
        """Collection of all Modality Nodes in the Project"""
        return self.children

    @property
    def compliant_modality_names(self) -> List[str]:
        """List of modality names which are compliant"""
        return self._compliant_children

    @property
    def non_compliant_modality_names(self) -> List[str]:
        """List of modality names which are not compliant"""
        return self._non_compliant_children

    def add_modality(self, new_modality: "Modality") -> None:
        """Add a new Modality Node to list of modalities in the Project

        Parameters
        ----------
        new_modality : base.Modality
            new modality node added to the Project
        """
        if not isinstance(new_modality, Modality):
            raise TypeError(
                "Expected argument of type <Modality>, got {} instead".format(
                    type(new_modality)))
        self.add(new_modality)

    def get_modality(self, name: str) -> Optional["Modality"]:
        """Fetch a Modality Node searching by its name. If name not found,
        returns None

        Parameters
        ----------
        name : str
            Key/Identifier to be searched in the dictionary

        Returns
        -------
        None or Modality
            value specified for key if key is in self._children
        """
        return self._get(name)

    def add_compliant_modality_name(self, modality_name: str) -> None:
        """
        Add modality name (which is fully compliant) to the list
        Parameters
        ----------
        modality_name : str
            Name to be added to list of compliant children
        """
        self._add_compliant_name(modality_name)

    def add_non_compliant_modality_name(self, modality_name: str) -> None:
        """Add modality name (which is not compliant) to the list

        Parameters
        ----------
        modality_name : str
            Name to be added to list of non-compliant modalities
        """
        self._add_non_compliant_name(modality_name)

    def save_dataset(self) -> None:
        """Saves dataset cache to disk for faster reloading"""
        if not self.modalities:
            raise EOFError('Dataset is empty!')
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load_dataset(self) -> None:
        """Loads dataset cache from disk"""
        if not self.cache_path.exists():
            raise FileNotFoundError('Provide a valid /path/to/cache/dir/')
        with open(self.cache_path, 'rb') as f:
            temp_dict = pickle.load(f)
            self.__dict__.update(temp_dict)


class Modality(Node):
    """
    Container to manage properties and issues at the modality level.
    Encapsulates all the details necessary for a modality.
    A single modality may contain multiple subjects, and each subject
    will have atleast single session.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    compliant: bool
        If the modality is fully compliant
    """

    def __init__(self, name):
        """Constructor
        Parameters
        ----------
        name : str
            Identifier/name for the modality. e.g. DTI-RL, fMRI
        """
        super().__init__(name)
        self._reference = dict()
        self.compliant = None

        cols = ['parameter', 'echo_time', 'ref_value', 'new_value', 'subjects']
        self.data = pd.DataFrame(columns=cols)

    def get_echo_times(self):
        """
        Different echo_times found for this modality in the project

        Returns
        -------
        list
            List of values
        """
        return list(self._reference.keys())

    def get_reference(self, echo_time=None) -> dict:
        """
        Get the reference protocol used to check compliance

        Parameters
        ----------
        echo_time : float
            Unique echo-time for a multi-echo modality

        Returns
        -------
        dict
            Key, Value pairs specifying the reference protocol
        """
        keys = self.get_echo_times()
        if len(self._reference) == 0:
            return None
        if self.is_multi_echo():
            if echo_time is None:
                raise LookupError("Specify echo_time for a multi-echo "
                                  "reference. Try one of {}".format(keys))
            reference = self._reference.get(echo_time, None)
            if reference is None:
                raise KeyError("Echo time {} absent. "
                               "Try one of {}".format(echo_time, keys))
            else:
                return reference
        else:
            _echo_time = keys[0]
            return self._reference[_echo_time]

    @property
    def subjects(self) -> List["Subject"]:
        """Collection of Subject Nodes in the Modality"""
        return self.children

    @property
    def compliant_subject_names(self) -> List[str]:
        """List of subject names which are compliant"""
        return self._compliant_children

    @property
    def non_compliant_subject_names(self) -> List[str]:
        """List of subject names which are not compliant"""
        return self._non_compliant_children

    def add_subject(self, new_subject) -> None:
        """Add a new Subject Node to list of subjects in the Modality

        Parameters
        ----------
        new_subject : base.Subject
            new subject node added to the Modality
        """
        if not isinstance(new_subject, Subject):
            raise TypeError(
                "Expected argument of type <Subject>, got {} instead".format(
                    type(new_subject)))
        self.add(new_subject)

    def add_compliant_subject_name(self, subject_name: str) -> None:
        """
        Add subject name (which is compliant) to the list

        Parameters
        ----------
        subject_name : str
            String value specifying a subject

        Returns
        -------

        """
        self._add_compliant_name(subject_name)

    def add_non_compliant_subject_name(self, subject_name) -> None:
        """Add subject name (which is not compliant) to the list"""
        self._add_non_compliant_name(subject_name)

    def get_subject(self, name) -> Optional["Subject"]:
        """
        Fetch a Subject Node searching by its name

        Parameters
        ----------
        name : str

        Returns
        -------
        None or Subject
            value specified for key if key is in self._children
        """
        return self._get(name)

    def set_reference(self, params: dict, echo_time=None, force=False) -> None:
        """Sets the reference protocol to check compliance

        Parameters
        ----------
        params : dict
            <Key, Value> pairs for parameters. e.g. Manufacturer : Siemens
        echo_time : float
            echo time to store different references for multi-echo modalities
        force : bool
            just do it
        """
        if not force:
            if echo_time is None:
                raise ValueError("Echo time required to store multiple "
                                 "references for multi-echo modalities. Set "
                                 "force to override and store single reference")
            else:
                self._reference[echo_time] = params.copy()
        else:
            echo_time = 1.0
            warnings.warn("Using a default value of 1.0 for echo time.")
            self._reference[echo_time] = params.copy()

    def is_multi_echo(self):
        """If the modality is multi-echo modality"""
        if len(self._reference) == 0:
            raise ValueError("Reference for modality not set. Use "
                             "set_reference first!")
        return len(self._reference) > 1

    def reasons_non_compliance(self, echo_time=None):
        if echo_time:
            query_str = "(echo_time==@echo_time)"
            db = self.data.query(query_str)
            return db['parameter'].unique()
        else:
            return self.data['parameter'].unique()

    def update_reason(self, param, te, ref, value, sub):
        query = [param, te, ref, value, sub]
        matches = (self.data == query).all(axis=1).any()
        if not matches:
            self.data.loc[len(self.data)] = query

    def query_reason(self, parameter, echo_time, column_name):
        # Do not remove brackets, seems redundant but code may break
        # See https://stackoverflow.com/a/57897625
        query_str = "(parameter==@parameter) & (echo_time==@echo_time)"
        db = self.data.query(query_str)
        colnames = list(self.data.columns)
        if column_name not in colnames:
            print(column_name)
            raise AttributeError('Expected one of {}. '
                                 'Got {}'.format(colnames, column_name))
        return db[column_name].unique()


class Subject(Node):
    """
    Container to manage properties and issues at the subject level.
    Encapsulates all the details necessary for a subject.
    A single subject may contain multiple sessions for a single modality.
    For a project called ABCD, it is grouped by modalities like T1, T2 etc.
    So, each modality, say T1 will have multiple subjects. And each subject
    can have multiple sessions.

    Attributes
    ----------
    name : str
        Identifier/name for the node

    """

    def __init__(self, name):
        super().__init__(name)

    @property
    def sessions(self) -> List["Session"]:
        """Collection of Session Nodes in the Subject"""
        return self.children

    def add_session(self, new_session) -> None:
        """Add a new Session Node to list of sessions in the Subject

        Parameters
        ----------
        new_session : base.Session
            new session node added to the Subject
        """
        if not isinstance(new_session, Session):
            raise TypeError(
                "Expected argument of type <Session>, got {} instead"
                "".format(type(new_session)))
        self.add(new_session)

    def get_session(self, name) -> Optional["Session"]:
        """        Fetch a Subject Node searching by its name"""
        return self._get(name)


class Session(Node):
    """
    Container to manage properties and issues at the session level.
    Encapsulates all the details necessary for a session.
    A single session may contain multiple runs

    Attributes
    ----------
    name : str
        Identifier/name for the Session
    path : str or Path
        filepath specifying the session directory
    params : dict
        Key, value pairs specifying the parameters for checking compliance
    """

    def __init__(self, name, path=None):
        """Constructor
        Parameters
        ----------
        name : str
            Identifier/name for the Session
        path : str or Path
            filepath specifying the Session directory
        """
        super().__init__(name)
        self.params = dict()
        if path:
            self.path = Path(path).resolve()
            if not self.path.exists():
                raise FileNotFoundError('Provide a valid /path/to/session/')

    @property
    def runs(self):
        """Collection of Run Nodes in the Session"""
        return self.children

    def add_run(self, new_run):
        """Add a new Run Node to list of runs in the Session

        Parameters
        ----------
        new_run : base.Run
            new run node added to the session
        """
        if not isinstance(new_run, Run):
            raise TypeError("Expected type <Run>, got {} instead"
                            .format(type(new_run)))
        self.add(new_run)

    def get_run(self, name):
        """Fetch a Run Node searching by its name"""
        return self._get(name)


class Run(Node):
    """
    Container to manage properties and issues at the run level.
    Encapsulates all the details necessary for a run. A run is a series of
    brain volumes. This is the lowest level in the hierarchy. Individual .dcm
    files should have same parameters at this level.
    """

    def __init__(self, name):
        """Constructor

        Parameters
        ----------
        name : str
            Identifier/name for the Run
        """
        super().__init__(name)
        self.echo_time = 0
        # TODO: check if self.error is required
        self.error = False
        self.params = dict()
        self.delta = None

