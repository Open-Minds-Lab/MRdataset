import logging
import pickle
from functools import total_ordering
from pathlib import Path
from typing import List, Optional, Type, Sized, Union

import pandas as pd

from MRdataset.utils import valid_dirs

logger = logging.getLogger('root')


@total_ordering
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
        Constructor for Node class

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
            raise TypeError("must be {}, not {}".format(
                type(Node),
                type(other)))
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

    def print_tree(self, markerStr: str = "+- ",
                   levelMarkers: Sized = None) -> None:
        """
        Adapted from
        https://simonhessner.de/python-3-recursively-print-structured-tree-including-hierarchy-markers-using-depth-first-search/
        Recursive function that prints the hierarchical structure of a tree
        including markers that indicate parent-child relationships between nodes

        Parameters
        ----------
        markerStr : str
            String to print in front of each node  ("+- " by default)
        levelMarkers : list
            Internally used by recursion to indicate where to print markers
            and connections
        """

        emptyStr = " " * len(markerStr)
        connectionStr = "|" + emptyStr[:-1]

        if levelMarkers is None:
            level = 0
            levelMarkers = []
        else:
            level = len(levelMarkers)

        def mapper(draw):
            # If the node is the last child, don't draw a connection
            return connectionStr if draw else emptyStr

        # Draw the markers for the current level
        markers = "".join(map(mapper, levelMarkers[:-1]))
        # Draw the marker for the current node
        markers += markerStr if level > 0 else ""
        # Print the node name
        print(f"{markers}{self.name}")

        # Recursively print the children
        for i, child in enumerate(self.children):
            # If the node is the last child, don't draw a connection
            isLast = i == len(self.children) - 1
            child.print_tree(markerStr, [*levelMarkers, not isLast])

    def __repr__(self) -> str:
        """String representation for developers"""
        return "<class MRdataset.base.{}({})>".format(self.__class__.__name__,
                                                      self.name)

    def __str__(self):
        """String representation for users"""
        if len(self.children) > 0:
            return "{} {} with {} {}".format(
                self.__class__.__name__,
                self.name,
                len(self.children),
                self.children[0].__class__.__name__)
        else:
            return "{} {} is empty. Use .walk()".format(self.__class__.__name__,
                                                        self.name)

    def __lt__(self, other):
        """Comparison operator for sorting"""
        if not isinstance(other, self.__class__):
            raise RuntimeError(f'< not supported between instances of '
                               f'{self.__class__.__name__} and '
                               f'{other.__class__.__name__}')
        return self.name < other.name

    def __eq__(self, other):
        """Comparison operator for equality"""
        if not type(other) == type(self):
            raise RuntimeError(f'== not supported between instances of '
                               f'{self.__class__.__name__} and '
                               f'{other.__class__.__name__}')
        if other._children == self._children:
            return True
        return False


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
        Constructor for Project class

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
        self.data_root = valid_dirs(data_root)

        self.metadata_root = Path(metadata_root)
        if not self.metadata_root.exists():
            self.metadata_root.mkdir(exist_ok=True)
            # raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        # TODO : Add a flag to identify instance as a subset
        self.cache_path = None
        self.set_cache_path()
        self.style = self.get_style()
        self.is_complete = True

    def walk(self):
        raise NotImplementedError("walk method must be implemented")

    def get_style(self):
        """
        Extracts style from classname
        For example, returns 'dicom', given DicomDataset class
        """
        classname = self.__class__.__name__.lower()
        style = classname.split('dataset')[0]
        return style

    def set_cache_path(self, path=None):
        """
        Sets cache path for the project
        Parameters
        ----------
        path: str or Path
            Path to cache file

        Returns
        -------
        None
        """
        if not path:
            self.cache_path = None
            # self.metadata_root / "{}{}".format(self.name, MRDS_EXT)
        else:
            self.cache_path = path

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
                "Expected argument of type {}, got {} instead".format(
                    type(Modality),
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

    def merge(self, other):
        """
        merges only at the subject level. Function would work if two partial
        datasets have mutually exclusive subjects in a single modality.
        Parameters
        ----------
        other: Project
            another partial dataset you want to merge with self.
        """
        logger.warning("Function is meant only for smooth "
                      " execution of ABCD dataset. "
                      "There is no guarantee on other datasets", stacklevel=2)
        # Add a check to ensure that the two datasets are of same type
        if not isinstance(other, Project):
            raise TypeError(f'Cannot merge MRdataset.Project and {type(other)}')
        # Add a check to ensure that the two datasets are of same style
        if self.style != other.style:
            raise TypeError(f'Cannot merge {self.style} and {other.style}')

        for modality in other.modalities:
            # Check if modality is present in Project
            exist_modality = self.get_modality(modality.name)
            # If modality doesn't exist
            if exist_modality is None:
                # Add modality to Project
                self.add_modality(modality)
                continue
            # If modality already exists
            for subject in modality.subjects:
                # Add subject to modality
                exist_modality.add_subject(subject)


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

    def __init__(self, name: str) -> None:
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
        self.non_compliant_data = pd.DataFrame(columns=cols)

    def get_echo_times(self) -> List[float]:
        """
        Different echo_times found for this modality in the project

        Returns
        -------
        list
            List of values
        """
        return list(self._reference.keys())

    def get_reference(self, echo_time: float = None) -> Optional[dict]:
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
                raise LookupError("Got NoneType for echo time."
                                  "Specify echo_time,"
                                  " use one of {}".format(keys))
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

    def add_subject(self, new_subject: 'Subject') -> None:
        """Add a new Subject Node to list of subjects in the Modality

        Parameters
        ----------
        new_subject : base.Subject
            new subject node added to the Modality
        """
        if not isinstance(new_subject, Subject):
            raise TypeError(
                "Expected argument of type {}, got {} instead".format(
                    type(Subject), type(new_subject)))
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

    def add_non_compliant_subject_name(self, subject_name: str) -> None:
        """Add subject name (which is not compliant) to the list"""
        self._add_non_compliant_name(subject_name)

    def get_subject(self, name: str) -> Optional["Subject"]:
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
            logging.info("Using a default value of 1.0 for echo time.")
            self._reference[echo_time] = params.copy()

    def is_multi_echo(self):
        """If the modality is multi-echo modality"""
        if len(self._reference) == 0:
            raise ValueError("Reference for modality not set. Use "
                             "set_reference first!")
        return len(self._reference) > 1

    def reasons_non_compliance(self, echo_time: float = None) -> dict:
        """
        Reasons for non-compliance in this modality across all the subjects.

        The following code uses the query method on the Pandas dataframe
        self.non_compliant_data to filter the rows based on query string
        "(echo_time == @echo_time)". This query string specifies that only
        rows where the value in the column 'echo_time' is equal to the value of
        the variable echo_time should be included in the resulting dataframe,
        denoted by the variable db. The @ symbol is used to indicate that the
        variable echo_time is a variable in the current namespace. The @ symbol
        is not required if the variable is a column in the dataframe.

        Parameters
        ----------
        echo_time

        Returns
        -------
        values : List[str]
            List of parameters that are non-compliant in this modality
        """
        if echo_time:
            query_str = "(echo_time==@echo_time)"
            db = self.non_compliant_data.query(query_str)
            return db['parameter'].unique()
        else:
            return self.non_compliant_data['parameter'].unique()

    def update(self, parameter: str, echo_time: float,
               reference: Union[str, float],
               new_value: Union[str, float], subject_name: str):
        """
        This function updates a DataFrame self.non_compliant_data with a new
        row of non_compliant_data.

        Parameters
        ----------
        parameter : str
            Parameter, for example, Manufacturer, EchoTime, etc.
        echo_time : float
            Echo time
        reference : str or float
            Reference value of the parameter
        new_value: str or float
            Value of the parameter for this subject
        subject_name: str
            Subject name

        Returns
        -------

        """
        # The function first creates a list query that contains all the
        # input values in the order they will appear in the new row.
        query = [parameter, echo_time, reference, new_value, subject_name]
        # Compares the DataFrame self.non_compliant_data with the query list.
        # The all method whether all the values in each row of
        # self.non_compliant_data are equal to the corresponding values
        # in the query list.
        # .any() method returns a single boolean value
        # indicating whether any of the rows in self.non_compliant_data
        # is equal to query.
        matches = (self.non_compliant_data == query).all(axis=1).any()
        if not matches:
            # If the query list is not present in self.non_compliant_data,
            # then the query list is appended to
            # self.non_compliant_data as a new row.
            # If matches is True, then the query list is already present
            # in self.non_compliant_data and no new row is added.
            self.non_compliant_data.loc[len(self.non_compliant_data)] = query

    def query(self, parameter: str,
              echo_time: float, column_name: str):
        """
        This function queries the DataFrame self.non_compliant_data to find the
        corresponding values for a given parameter and echo time.
        The function is used in mrQA to find the reference value, the subject
        name, the parameter value for this subject. The function is
        used to create the report of non-compliant subjects.

        Parameters
        ----------
        parameter : str
            Parameter, for example, Manufacturer, EchoTime, etc.
        echo_time : float
            Echo time
        column_name : str
            Name of the column to query.
            One of ['ref_value', 'new_value', 'subjects']

        Returns
        -------
        values : List[str]
        """
        # Do not remove brackets, seems redundant but code may break
        # See https://stackoverflow.com/a/57897625
        query_str = "(parameter==@parameter) & (echo_time==@echo_time)"
        db = self.non_compliant_data.query(query_str)
        colnames = list(self.non_compliant_data.columns)
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
        """
        Constructor for Subject class

        Parameters
        ----------
        name : str
            Identifier/name for the Subject node
        """
        super().__init__(name)

    @property
    def sessions(self) -> List["Session"]:
        """Collection of Session Nodes in the Subject"""
        return self.children

    def add_session(self, new_session) -> None:
        """Add a new Session Node to list of sessions in the Subject

        Parameters
        ----------
        new_session : Session
            new session node added to the Subject
        """
        if not isinstance(new_session, Session):
            raise TypeError(
                "Expected argument of type {}, got {} instead"
                "".format(type(Session), type(new_session)))
        self.add(new_session)

    def get_session(self, name) -> Optional["Session"]:
        """
        Fetch a Session Node searching by its name
        Parameters
        ----------
        name : str
            Identifier/name for the Session Node

        Returns
        -------
        None or Session
        """
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
        new_run : Run
            new run node added to the session
        """
        if not isinstance(new_run, Run):
            raise TypeError("Expected type {}, got {} instead"
                            .format(type(Run), type(new_run)))
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
