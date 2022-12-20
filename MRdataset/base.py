import logging
import pickle
from functools import total_ordering
from pathlib import Path
from typing import List, Optional, Type, Sized, Union
from MRdataset.config import MRDS_EXT
import pandas as pd

from MRdataset.utils import valid_dirs

from MRdataset.log import logger


@total_ordering
class Node:
    """
    An abstract class specifying a generic node in a neuroimaging experiment.
    It is inherited to create subclasses like BaseDataset, Modality, Subject etc.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    """

    def __init__(self, **kwargs) -> None:
        """
        Constructor for Node class

        Parameters
        ----------
        kwargs : dict
            Additional keyword arguments passed to Node
        """
        self.name = None
        self._sub_nodes = dict()
        self._compliant_list = list()
        self._non_compliant_list = list()

    @property
    def sub_nodes(self):
        """
        Each node can be connected to several sub nodes, generally
        subcomponents of Node
        """
        return list(self._sub_nodes.values())

    @property
    def compliant_list(self):
        """
        Each node can be connected to several compliant sub nodes
        """
        return self._compliant_list

    @property
    def non_compliant_list(self):
        """
        Each node can be connected to several non-compliant sub nodes
        """
        return self._non_compliant_list

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
        self._sub_nodes[other.name] = other

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
        return self._sub_nodes.get(name, None)

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
        if other in self.compliant_list:
            return
        self.compliant_list.append(other)

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
        if other in self._non_compliant_list:
            return
        self.non_compliant_list.append(other)

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
        for i, sub_node in enumerate(self.sub_nodes):
            # If the node is last, don't draw a connection
            isLast = i == len(self.sub_nodes) - 1
            sub_node.print_tree(markerStr, [*levelMarkers, not isLast])

    def __repr__(self) -> str:
        """String representation for developers"""
        return "<class MRdataset.base.{}({})>".format(self.__class__.__name__,
                                                      self.name)

    def __str__(self):
        """String representation for users"""
        if len(self.sub_nodes) > 0:
            return "{} {} with {} {}".format(
                self.__class__.__name__,
                self.name,
                len(self.sub_nodes),
                self.sub_nodes[0].__class__.__name__)
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
        if other.sub_nodes == self.sub_nodes:
            return True
        return False

    def __nonzero__(self):
        """
        Returns True if the node is not empty, at that level. False otherwise.
        """
        if len(self.sub_nodes) > 0:
            return True
        else:
            return False


class BaseDataset(Node):
    """
    Container to manage properties and issues at the project level.
    Encapsulates all the details necessary for a complete project.
    A single dataset may contain multiple modalities, and each modality
    expected to have atleast single subject.

    Attributes
    ----------
    name : str
        Identifier/name for the dataset
    data_source_folders : str or Path
        directory containing dataset files such as dcm, nii, json, etc
    """

    def __init__(self, data_source_folders, **kwargs):
        """
        Constructor for BaseDataset class

        Parameters
        ----------
        name : str
            Identifier/name for the node
        data_source_folders : str or Path
            directories containing dataset with dicom files
        kwargs : dict
            Additional keyword arguments passed to BaseDataset
        """
        super().__init__()
        # Manage directories
        if data_source_folders:
            self.data_source_folders = valid_dirs(data_source_folders)
        else:
            self.data_source_folders = None
        # TODO : Add a flag to identify instance as a subset
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
        if 'dataset' in classname:
            style = classname.split('dataset')[0]
        else:
            raise ValueError("Expected classname with keyword 'dataset'. "
                             "For example, DicomDataset, BIDSDataset. Got"
                             "{0} instead. Rename the class as "
                             "{0}Dataset".format(classname))
        return style

    @property
    def modalities(self) -> List["Modality"]:
        """Collection of all Modality Nodes in the BaseDataset"""
        return self.sub_nodes

    @property
    def compliant_modality_names(self) -> List[str]:
        """List of modality names which are compliant"""
        return self.compliant_list

    @property
    def non_compliant_modality_names(self) -> List[str]:
        """List of modality names which are not compliant"""
        return self.non_compliant_list

    def add_modality(self, new_modality: "Modality") -> None:
        """Add a new Modality Node to list of modalities in the BaseDataset

        Parameters
        ----------
        new_modality : base.Modality
            new modality node added to the BaseDataset
        """
        if not isinstance(new_modality, Modality):
            raise TypeError(
                "Expected argument of type {}, got {} instead".format(
                    type(Modality),
                    type(new_modality)))
        self.add(new_modality)

    def get_modality_by_name(self, modality_name: str) -> Optional["Modality"]:
        """Fetch a Modality Node searching by its name. If name not found,
        returns None

        Parameters
        ----------
        modality_name : str
            Key/Identifier to be searched in the dictionary

        Returns
        -------
        None or Modality
            value specified for key if key is in self._children
        """
        return self._get(modality_name)

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

    def update_data_sources(self, values: Union[str, Path, list]) -> None:
        """Update data source folders for the dataset"""

        if isinstance(self.data_source_folders, list):
            if isinstance(values, list):
                self.data_source_folders.extend(values)
            elif isinstance(values, str) or isinstance(values, Path):
                self.data_source_folders.append(Path(values))
            else:
                raise TypeError(f"Expected str or Path or List[str or Path], "
                                f"got {type(values)}")
        elif isinstance(self.data_source_folders, str) \
                or isinstance(self.data_source_folders, Path):
            if isinstance(values, list):
                self.data_source_folders = [self.data_source_folders]
                self.data_source_folders.extend(values)
            elif isinstance(values, str) or isinstance(values, Path):
                self.data_source_folders = [self.data_source_folders,
                                            Path(values)]
            else:
                raise TypeError(f"Expected str or Path or List[str or Path],"
                                f" got {type(values)}")
        else:
            raise TypeError(f"Expected str or Path or List[str or Path], got "
                            f"{type(self.data_source_folders)}")

    def merge(self, other: "BaseDataset") -> None:
        """
        Merges at the subject level. Function would work if two partial
        datasets have mutually exclusive subjects in a single modality.

        Parameters
        ----------
        other: BaseDataset
            another partial dataset you want to merge with self.
        """
        logger.info("Function is meant only for smooth "
                    " execution of ABCD dataset. "
                    "There is no guarantee on other datasets")
        # Add a check to ensure that the two datasets are of same type
        if not isinstance(other, BaseDataset):
            raise TypeError(f'Cannot merge MRdataset.BaseDataset and {type(other)}')
        # Add a check to ensure that the two datasets are of same style
        if self.style != other.style:
            raise TypeError(f'Cannot merge {self.style} and {other.style}')

        self.update_data_sources(other.data_source_folders)

        for modality in other.modalities:
            # Check if modality is present in self
            exist_modality = self.get_modality_by_name(modality.name)
            # If modality doesn't exist
            if exist_modality is None:
                # Add modality to self, which would also add all subjects
                # inside it
                self.add_modality(modality)
                continue
            # If modality already exists, add all the subjects in it
            # Remember, the subjects are exclusive in both the datasets
            # because of the way the jobs were split
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
        Identifier/name for the modality
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
        keys = list(self.get_echo_times())
        if len(self._reference) == 0:
            return None
        elif len(self._reference) == 1:
            return self._reference[keys[0]]
        else:
            if echo_time is None:
                raise LookupError("Got NoneType for echo time. "
                                  "Specify echo_time, "
                                  "Use one of {}".format(keys))
            if echo_time not in keys:
                raise LookupError("Echo time {} not found. "
                                  "Use one of {}".format(echo_time, keys))
            return self._reference[echo_time]

    @property
    def subjects(self) -> List["Subject"]:
        """Collection of Subject Nodes in the Modality"""
        return self.sub_nodes

    @property
    def compliant_subject_names(self) -> List[str]:
        """List of subject names which are compliant"""
        return self._compliant_list

    @property
    def non_compliant_subject_names(self) -> List[str]:
        """List of subject names which are not compliant"""
        return self._non_compliant_list

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

    def get_subject_by_name(self, subject_name: str) -> Optional["Subject"]:
        """
        Fetch a Subject Node searching by its name

        Parameters
        ----------
        subject_name : str

        Returns
        -------
        None or Subject
            value specified for key if key is in self._children
        """
        return self._get(subject_name)

    def set_reference(self, params: dict, echo_time=None) -> None:
        """Sets the reference protocol to check compliance

        Parameters
        ----------
        params : dict
            <Key, Value> pairs for parameters. e.g. Manufacturer : Siemens
        echo_time : float
            echo time to store different references for multi-echo modalities
        """

        if echo_time is None:
            echo_time = 1.0
            logger.info("echo time is not specified! Using a value of 1.0.")

        self._reference[echo_time] = params.copy()

    def is_multi_echo(self) -> bool:
        """If the modality is multi-echo modality"""
        if len(self._reference) == 0:
            raise ValueError("Reference for modality not set. Use "
                             "set_reference first!")
        return len(self._reference) > 1

    def non_compliant_params(self, echo_time: float = None) -> dict:
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

    def add_non_compliant_param(self, parameter: str, echo_time: float,
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

    def query_by_param(self, parameter: str,
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
        column_names = list(self.non_compliant_data.columns)
        if column_name not in column_names:
            print(column_name)
            raise AttributeError('Expected one of {}. '
                                 'Got {}'.format(column_names, column_name))
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

    def __init__(self, name: str):
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
        return self.sub_nodes

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

    def get_session_by_name(self, session_name: str) -> Optional["Session"]:
        """
        Fetch a Session Node searching by its name
        Parameters
        ----------
        session_name : str
            Identifier/name for the Session Node

        Returns
        -------
        None or Session
        """
        return self._get(session_name)


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

    def __init__(self, name: str):
        """Constructor
        Parameters
        ----------
        name : str
            Identifier/name for the Session
        """
        super().__init__(name)
        self.params = dict()

    @property
    def runs(self):
        """Collection of Run Nodes in the Session"""
        return self.sub_nodes

    def add_run(self, new_run: "Run") -> None:
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

    def get_run_by_name(self, run_name: str) -> Optional["Run"]:
        """Fetch a Run Node searching by its name"""
        return self._get(run_name)


class Run(Node):
    """
    Container to manage properties and issues at the run level.
    Encapsulates all the details necessary for a run. A run is a series of
    brain volumes. This is the lowest level in the hierarchy. Individual .dcm
    files should have same parameters at this level.
    """

    def __init__(self, name: str):
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
