"""Module containing the base class for all MRdataset objects"""
from functools import total_ordering
from pathlib import Path
from typing import List, Optional, Type, Sized, Union

import pandas as pd
from MRdataset.log import logger


@total_ordering
class Node:
    """
    The class specifies a generic element in a neuroimaging experiment.
    It is inherited to create subclasses like BaseDataset, Modality, Subject
    etc.

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
        self._sub_nodes = {}
        self._compliant_list = set()
        self._non_compliant_list = set()
        self.compliant = True

    def reset_lists(self):
        """
        Clears the compliance of the node
        """
        self.compliant = True
        self._compliant_list = set()
        self._non_compliant_list = set()

    @property
    def sub_nodes(self):
        """
        Each node can be connected to several sub nodes, generally
        subcomponents of Node
        """
        return sorted(list(self._sub_nodes.values()))

    @property
    def compliant_list(self):
        """
        Each node can maintain a list of compliant sub nodes
        """
        # TODO: Check if casting to list is required, or we can just return
        # a set
        return list(self._compliant_list)

    @property
    def non_compliant_list(self):
        """
        Each node can maintain a list of compliant sub nodes
        """
        # TODO: Check if casting to list is required, or we can just return
        # a set
        return list(self._non_compliant_list)

    def add_sub_node(self, other: 'Node') -> None:
        """
        Adds a sub-node to self._sub_nodes dict, if already present
        updates it

        Parameters
        ----------
        other : Node
            another Node object that must be added to list of sub_nodes

        Raises
        ------
        TypeError
            If other is not of type Node
        """
        # TODO: consider adding either __copy__ or __deepcopy__ to Node
        if not isinstance(other, Node):
            raise TypeError(f'must be {type(Node)}, not {type(other)}')
        self._sub_nodes[other.name] = other

    def get_sub_node_by_name(self, name: str) -> Optional[Type['Node']]:
        """
        Fetches a sub_node which has the same key as 'name'. If key is not
        available, returns None

        Parameters
        ----------
        name : str
            Key/Identifier to be searched in the dictionary

        Returns
        -------
        None or Node
            value specified for key if key is in self.sub_nodes
        """
        return self._sub_nodes.get(name, None)

    def _add_compliant_name(self, other: str) -> None:
        """
        Add a name to list of compliant sub_nodes

        Parameters
        ----------
        other : str
            Name to be added to list of compliant sub_nodes

        Raises
        ------
        TypeError
            If other is not of type str
        """
        if not isinstance(other, str):
            raise TypeError(f'must be str, not {type(other)}')
        if other in self._compliant_list:
            return
        self._compliant_list.add(other)

    def _add_non_compliant_name(self, other: str) -> None:
        """
        Add a name to list of non-compliant sub_nodes

        Parameters
        ----------
        other : str
            Name to be added to list of non-compliant sub_nodes

        Raises
        ------
        TypeError
            If other is not of type str
        """
        if not isinstance(other, str):
            raise TypeError(f'must be str, not {type(other)}')
        if other in self._non_compliant_list:
            return
        self._non_compliant_list.add(other)

    def print_tree(self, marker_str: str = '+- ',
                   level_markers: Sized = None) -> None:
        """
        Adapted from
        https://simonhessner.de/python-3-recursively-print-structured-tree-including-hierarchy-markers-using-depth-first-search/
        Recursive function that prints the hierarchical structure of a tree
        including markers that indicate parent-child relationships between nodes

        Parameters
        ----------
        marker_str : str
            String to print in front of each node  ('+- ' by default)
        level_markers : list
            Internally used by recursion to indicate where to print markers
            and connections
        """

        empty_str = ' ' * len(marker_str)
        connection_str = '|' + empty_str[:-1]

        if level_markers is None:
            level = 0
            level_markers = []
        else:
            level = len(level_markers)

        def mapper(draw):
            # If the sub_node is the last sub_node, don't draw a connection
            return connection_str if draw else empty_str

        # Draw the markers for the current level
        markers = ''.join(map(mapper, level_markers[:-1]))
        # Draw the marker for the current node
        markers += marker_str if level > 0 else ''
        # Print the node name
        print(f'{markers}{self.name}')

        # Recursively print the sub_nodes
        for i, sub_node in enumerate(self.sub_nodes):
            # If the node is last, don't draw a connection
            is_last = i == len(self.sub_nodes) - 1
            sub_node.print_tree(marker_str, [*level_markers, not is_last])

    def __repr__(self) -> str:
        """String representation for developers"""
        return f'<class MRdataset.base.{self.__class__.__name__}({self.name})>'

    def __str__(self):
        """String representation for users"""
        if len(self.sub_nodes) > 0:
            return f'{self.__class__.__name__} {self.name} with ' \
                   f'{len(self.sub_nodes)} ' \
                   f'{self.sub_nodes[0].__class__.__name__}'
        else:
            return f'{self.__class__.__name__} {self.name} is empty.'

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
        return len(self.sub_nodes) > 0


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
    data_source : str or Path
        directory containing dataset files such as dcm, nii, json, etc
    """

    def __init__(self, data_source, **kwargs):
        """
        Constructor for BaseDataset class

        Parameters
        ----------
        name : str
            Identifier/name for the node
        data_source : str or Path
            directories containing dataset with dicom files
        kwargs : dict
            Additional keyword arguments passed to BaseDataset
        """
        super().__init__()
        # Manage directories
        if isinstance(data_source, str):
            data_source = [data_source]
        self.data_source = data_source

        self.ds_format = self.get_ds_format()
        self.is_complete = True

    def walk(self):
        """
        Walks through the dataset and creates a tree of nodes
        """
        raise NotImplementedError('walk method must be implemented')

    def get_ds_format(self):
        """
        Extracts ds_format from classname
        For example, returns 'dicom', given DicomDataset class
        """
        classname = self.__class__.__name__.lower()
        if 'dataset' in classname:
            ds_format = classname.split('dataset', maxsplit=1)[0]
        else:
            raise ValueError("Expected classname with keyword 'dataset'. "
                             'For example, DicomDataset, BIDSDataset. Got'
                             f'{classname} instead. Rename the class as '
                             f'{classname}Dataset')
        return ds_format

    @property
    def modalities(self) -> List['Modality']:
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

    def add_modality(self, new_modality: 'Modality') -> None:
        """Add a new Modality Node to list of modalities in the BaseDataset

        Parameters
        ----------
        new_modality : base.Modality
            new modality node added to the BaseDataset
        """
        if not isinstance(new_modality, Modality):
            raise TypeError(
                f'Expected argument of type {type(Modality)}, '
                f'got {type(new_modality)} instead')
        self.add_sub_node(new_modality)

    def get_modality_by_name(self, modality_name: str) -> Optional['Modality']:
        """Fetch a Modality Node searching by its name. If name not found,
        returns None

        Parameters
        ----------
        modality_name : str
            Key/Identifier to be searched in the dictionary

        Returns
        -------
        None or Modality
            value specified for key if key is in self.sub_nodes
        """
        return self.get_sub_node_by_name(modality_name)

    def add_compliant_modality_name(self, modality_name: str) -> None:
        """
        Add modality name (which is fully compliant) to the list
        Parameters
        ----------
        modality_name : str
            Name to be added to list of compliant sub_nodes
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

    def amend_data_src_attribute(self, values: Union[str, Path, list]) -> None:
        """Update data source folders for the dataset"""
        if not isinstance(self.data_source, list):
            list1 = [self.data_source]
        else:
            list1 = self.data_source

        if not isinstance(values, list):
            list2 = [values]
        else:
            list2 = values

        combined_list = list1.extend(list2)
        self.data_source = combined_list

    def merge(self, other: 'BaseDataset') -> None:
        """
        The merging process starts on the modalities level, and it gradually
        traverses down the tree until all nodes are merged.

        This function merges two trees by traversing each level of the second
        tree (i.e. other) and finding its corresponding node in the
        first tree (i.e. self) using the get_func.

        If an exising node is not found in first tree which has same name as the
        new_node from second tree, new_node is added to the first tree using
        the add_func. If a existing node is found, the function recursively
        calls itself with list of sub_nodes (other_list) in new_node.
        Then it checks if all sub_nodes are present in the existing node.

        The process continues until all nodes in both trees have been merged
        and a single merged tree is created.

        Parameters
        ----------
        other: BaseDataset
            another partial dataset you want to merge with self.
        """
        logger.info('Function is meant only for smooth '
                    ' execution of ABCD dataset. '
                    'There is no guarantee on other datasets')
        # Add a check to ensure that the two datasets are of same type
        if not isinstance(other, BaseDataset):
            raise TypeError(
                f'Cannot merge MRdataset.BaseDataset and {type(other)}')
        # Add a check to ensure that the two datasets are of same ds_format
        if self.ds_format != other.ds_format:
            raise TypeError(f'Cannot merge {self.ds_format} and {other.ds_format}')

        self.amend_data_src_attribute(other.data_source)

        def traverse_and_add(get_sub_node_func,
                             other_sub_node_list,
                             add_sub_node_func):
            """
            The merging process starts on the modalities level, and it gradually
            traverses down the tree recursively until all nodes are merged.

            Parameters
            ----------
            get_sub_node_func : Callable
                Function to get a sub_node from the current node
            other_sub_node_list : List
                List of sub_nodes to be merged
            add_sub_node_func: Callable
                Function to add a sub_node to the current node

            Returns
            -------
            None
            """
            for new_item in other_sub_node_list:
                existing_item = get_sub_node_func(new_item.name)
                if existing_item:
                    if len(new_item.sub_nodes) > 0:
                        traverse_and_add(existing_item.get_sub_node_by_name,
                                         new_item.sub_nodes,
                                         existing_item.add_sub_node)
                else:
                    add_sub_node_func(new_item)

        # The merging process starts on the modalities level, and it gradually
        # traverses down the tree recursively until all nodes are merged.
        traverse_and_add(get_sub_node_func=self.get_modality_by_name,
                         other_sub_node_list=other.modalities,
                         add_sub_node_func=self.add_sub_node)

        # for modality in other.modalities:
        #     # Check if modality is present in self
        #     exist_modality = self.get_modality_by_name(modality.name)
        #     # If modality doesn't exist
        #     if exist_modality is None:
        #         # Add modality to self, which would also add all subjects
        #         # inside it
        #         self.add_modality(modality)
        #         continue
        #     # If modality already exists, add all the subjects in it
        #     # Remember, the subjects are exclusive in both the datasets
        #     # because of the way the jobs were split
        #     for subject in modality.subjects:
        #         # Add subject to modality
        #         exist_modality.add_subject(subject)


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
        """
        Constructor

        Parameters
        ----------
        name : str
            Identifier/name for the modality. e.g. DTI-RL, fMRI
        """
        super().__init__()
        self._reference = {}
        self.name = name
        self.non_compliant_data = None
        self._error_subject_names = []
        self.reset_compliance()

    def reset_compliance(self):
        self.reset_lists()
        for subject in self.subjects:
            for session in subject.sessions:
                for run in session.runs:
                    run.reset_lists()
                session.reset_lists()
            subject.reset_lists()

        self._reference = {}
        self._error_subject_names = []
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
                raise LookupError('Got NoneType for echo time. '
                                  'Specify echo_time, '
                                  f'Use one of {keys}')
            if echo_time not in keys:
                raise LookupError(f'Echo time {echo_time} not found. '
                                  f'Use one of {keys}')
            return self._reference[echo_time]

    @property
    def subjects(self) -> List['Subject']:
        """Collection of Subject Nodes in the Modality"""
        return self.sub_nodes

    @property
    def compliant_subject_names(self) -> List[str]:
        """List of subject names which are compliant"""
        return self.compliant_list

    @property
    def non_compliant_subject_names(self) -> List[str]:
        """List of subject names which are not compliant"""
        return self.non_compliant_list

    def add_subject(self, new_subject: 'Subject') -> None:
        """Add a new Subject Node to list of subjects in the Modality

        Parameters
        ----------
        new_subject : base.Subject
            new subject node added to the Modality
        """
        if not isinstance(new_subject, Subject):
            raise TypeError(
                f'Expected argument of type {type(Subject)}, '
                f'got {type(new_subject)} instead')
        self.add_sub_node(new_subject)

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

    def error_subject_names(self) -> List:
        """Add subject/sessions for which majority could not
        be could not be computed
        """
        return self._error_subject_names

    def add_error_subject_names(self, value):
        if not hasattr(self, '_error_subject_names'):
            self._error_subject_names = []
        self._error_subject_names.append(value)

    def get_subject_by_name(self, subject_name: str) -> Optional['Subject']:
        """
        Fetch a Subject Node searching by its name

        Parameters
        ----------
        subject_name : str
            String value specifying a subject

        Returns
        -------
        None or Subject
            value specified for key if key is in self.sub_nodes
        """
        return self.get_sub_node_by_name(subject_name)

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
            logger.info('echo time is not specified! Using a value of 1.0.')

        self._reference[echo_time] = params.copy()

    def is_multi_echo(self) -> bool:
        """If the modality is multi-echo modality"""
        if len(self._reference) == 0:
            raise ValueError('Reference for modality not set. Use '
                             'set_reference first!')
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
            query_str = '(echo_time==@echo_time)'
            db = self.non_compliant_data.query(query_str)
            return db['parameter'].unique()
        else:
            return self.non_compliant_data['parameter'].unique()

    def add_non_compliant_param(self, parameter: str, echo_time: float,
                                reference: Union[str, float],
                                new_value: Union[str, float, None],
                                subject_name: str):
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

        Raises
        _SpecialForm
        """
        # Do not remove brackets, seems redundant but code may break
        # See https://stackoverflow.com/a/57897625
        query_str = '(parameter==@parameter) & (echo_time==@echo_time)'
        db = self.non_compliant_data.query(query_str)
        column_names = list(self.non_compliant_data.columns)
        if column_name not in column_names:
            print(column_name)
            raise AttributeError(f'Expected one of {column_names}. '
                                 f'Got {column_name}')
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
        super().__init__()
        self.name = name

    @property
    def sessions(self) -> List['Session']:
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
                f'Expected argument of type {type(Session)}, '
                f'got {type(new_session)} instead')
        self.add_sub_node(new_session)

    def get_session_by_name(self, session_name: str) -> Optional['Session']:
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
        return self.get_sub_node_by_name(session_name)

    def add_compliant_session_name(self, session_name: str) -> None:
        """
        Add session name (which is compliant) to the list

        Parameters
        ----------
        session_name : str
            String value specifying a session

        Returns
        -------

        """
        self._add_compliant_name(session_name)

    def add_non_compliant_session_name(self, session_name: str) -> None:
        """Add session name (which is not compliant) to the list"""
        self._add_non_compliant_name(session_name)


class Session(Node):
    """
    Container to manage properties and issues at the session level.
    Encapsulates all the details necessary for a session.
    A single session may contain multiple runs

    Attributes
    ----------
    name : str
        Identifier/name for the Session
    params : dict
        Key, value pairs specifying the parameters for checking compliance
    """

    def __init__(self, name: str):
        """
        Constructor

        Parameters
        ----------
        name : str
            Identifier/name for the Session
        """
        super().__init__()
        self.name = name
        self.params = {}

    @property
    def runs(self):
        """Collection of Run Nodes in the Session"""
        return self.sub_nodes

    def add_run(self, new_run: 'Run') -> None:
        """Add a new Run Node to list of runs in the Session

        Parameters
        ----------
        new_run : Run
            new run node added to the session

        Raises
        ------
        TypeError
            If the new_run is not of type Run
        """
        if not isinstance(new_run, Run):
            raise TypeError(f'Expected type {type(Run)}, '
                            f'got {type(new_run)} instead')
        self.add_sub_node(new_run)

    def get_run_by_name(self, run_name: str) -> Optional['Run']:
        """Fetch a Run Node searching by its name"""
        return self.get_sub_node_by_name(run_name)


class Run(Node):
    """
    Container to manage properties and issues at the run level.
    Encapsulates all the details necessary for a run. A run is a series of
    brain volumes. This is the lowest level in the hierarchy. Individual .dcm
    files should have same parameters at this level.
    """

    def __init__(self, name: str):
        """
        Constructor

        Parameters
        ----------
        name : str
            Identifier/name for the Run
        """
        super().__init__()
        self.name = name
        self.echo_time = 0
        # TODO: check if self.error is required
        self.error = False
        self.params = {}
        self.delta = None

    def reset_lists(self):
        """
        Clears the compliance of the node
        """
        self.compliant = True
        self._compliant_list = set()
        self._non_compliant_list = set()
        self.delta = None
