from abc import ABC, abstractmethod
from itertools import product
from pathlib import Path
from typing import List, Union

from MRdataset import logger
from MRdataset.config import VALID_DATASET_FORMATS
from MRdataset.utils import valid_dirs, convert2ascii
from protocol import BaseSequence


# class Run(UserDict):
#     """Container for an imaging run.
#
#     Design:
#     - A run is an instance of a sequence
#     - A session can have multiple runs acquired with the same
#           sequence/parameters
#     - for only a SINGLE subject
#
#     """
#
#     def __init__(self,
#                  session_id: str = 'SessionID',
#                  subject_id: str = 'SubjectID',
#                  sequence: ImagingSequence = None):
#         """constructor"""
#
#         super().__init__()
#         self.session_id = session_id
#         self.subject_id = subject_id
#         self.sequence = sequence
#
#
# class Session(UserDict):
#     """Container for an imaging session.
#
#     Design:
#     - A session is a collection of runs,
#         and each run is different acquisition with the same
#         sequence/parameters
#     - for only a SINGLE subject
#     - like a Visit in longitudinal studies
#     """
#
#     def __init__(self,
#                  session_id='SessionID',
#                  subject_id='SubjectID',
#                  runs: List[Run] = None):
#         """constructor"""
#
#         super().__init__()
#         self.session_id = session_id
#         self.subject_id = subject_id
#         self.runs = runs
#
#
# class Subject(UserDict):
#     """base class for all subjects"""
#
#     def __init__(self,
#                  subject_id='SubjectID',
#                  sessions: List[Session] = None):
#         """constructor"""
#
#         super().__init__()
#         self.subject_id = subject_id
#         self.sessions = sessions

class BaseDataset(ABC):
    """
    Base class for all datasets. The class provides a common interface to access
    the dataset in a hierarchical fashion. The hierarchy is as follows:
    Subject > Session > Sequence > Run

    Parameters
    ----------
    data_source : List | Path | str
        valid path to the dataset on disk
    is_complete : bool
        flag to indicate if the dataset is complete or not
    name : str
        name of the dataset
    ds_format : str
        format of the dataset. One of ['dicom', 'bids']
    """

    # self._subj_ids : set
    #     List of unique subject IDs in the entire dataset.
    # self._seq_ids : set
    #     List of unique sequence IDs in the dataset.
    # self._seqs_map : dict
    #     Dictionary mapping sequence IDs to corresponding
    #     (subject_id, session_id, run_id) tuples
    # self._sess_map : dict
    #     Dictionary mapping session IDs to corresponding sequence IDs
    # self._tree_map : dict
    #     A hierarchical representation of the dataset, storing data
    #     in a tree-like structure with subjects as the root, sessions as
    #     children of subjects, sequences as children of sessions, and
    #     runs as children of sequences.
    # self._flat_map : dict
    #     A flat representation of the dataset, storing data in
    #     a dictionary where keys are tuples (subj_id, sess_id, seq_id, run_id)
    #     and values are the corresponding protocol.BaseSequence for that
    #     specific run.
    # """
    def __init__(self,
                 data_source: Union[List, Path, str] = None,
                 is_complete: bool = True,
                 name: str = 'Dataset',
                 ds_format: str = 'dicom'):
        """constructor"""

        self.data_source = valid_dirs(data_source)
        self.name = convert2ascii(name)

        if ds_format not in VALID_DATASET_FORMATS:
            raise ValueError(f'Invalid dataset format {ds_format}')
        self.format = ds_format

        self.is_complete = is_complete

        self._subj_ids = set()
        self._seq_ids = set()

        self._tree_map = dict()
        self._flat_map = dict()

        self._seqs_map = dict()
        self._sess_map = dict()

        self._saved_path = ''
        # self.data_source[0] / "mrdataset" / "mrdataset.pkl"
        self._reloaded = False
        self._process_whole_folder = dict()
        self._key_vars = set(['_flat_map',  # noqa
                              '_tree_map',
                              '_seqs_map',
                              '_sess_map',
                              '_subj_ids',
                              '_seq_ids',
                              'format',
                              'name',
                              'root',
                              'subjects'])

    def get_sequence_ids(self):
        """Returns a list of all sequence IDs in the dataset"""
        # Cast to list so that it can be indexed, set is not subscript-able
        return sorted(self._seq_ids)

    def subjects(self):
        """Returns a list of all subject IDs in the dataset"""
        return sorted(self._subj_ids)

    def get_subject_ids(self, seq_id):
        """
        Returns a list of all subject IDs in the dataset for a given sequence ID

        Parameters
        ----------
        seq_id : str
            Name of the Sequence ID
        """
        if not isinstance(seq_id, str):
            raise TypeError('seq_id must be a string')
        if seq_id not in self._seqs_map.keys():
            return []

        # seqs map is a set of tuples (subj, sess, run)
        tuples = self._seqs_map[seq_id]
        subj_ids = set([t[0] for t in tuples])

        # Cast to list so that it can be indexed, set is not subscriptable
        return sorted(subj_ids)

    # def _reload_saved(self):
    #     """helper to reload previously saved MRdataset"""
    #
    #     if len(self._subj_ids) > 0 and self._reloaded:
    #         print('Dataset seems to be loaded already. Skipping reload!')
    #
    #     try:
    #         print('reloading previously parsed MRdataset ...')
    #         with open(self._saved_path, 'rb') as in_file:
    #             prev = pickle.load(in_file)
    #         for attr in self._key_vars:
    #             self.__setattr__(attr, getattr(prev, attr))
    #     except Exception as exc:
    #         print(f' unable to reload from {self._saved_path}')
    #         raise exc
    #     else:
    #         self._reloaded = True
    #         print(self)

    @abstractmethod
    def load(self):
        """default method to load the dataset"""

    def _tree_add_node(self, subject_id, session_id, seq_id, run_id,
                       seq_info):
        """
        A hierarchical representation of the dataset, storing data
        in a tree-like structure with subjects as the root, sessions as children
        of subjects, sequences as children of sessions, and runs as children of
        sequences.

        Parameters
        ----------
        subject_id : str
            Unique identifier for the Subject. For example, a subject ID can be
            a string like 'sub-01' or '001'.
        session_id : str
            Unique identifier the Session. For example, a session ID can be
            a string like 'ses-01' or '001'. For DICOM datasets, this can be
            StudyInstanceUID.
        seq_id : str
            Unique identifier the Sequence. For example, a sequence ID can be
            a string like 'fMRI' or 't1w'.
        run_id : str
            Unique identifier the Run. For example, a run ID can be
            a string like 'run-01' or '001'. For DICOM datasets, this can be
            SeriesInstanceUID.
        seq_info : protocol.BaseSequence
            Instance of the sequence
        """
        if subject_id not in self._tree_map:
            self._tree_map[subject_id] = dict()

        if session_id not in self._tree_map[subject_id]:
            self._tree_map[subject_id][session_id] = dict()

        if seq_id not in self._tree_map[subject_id][session_id]:
            self._tree_map[subject_id][session_id][seq_id] = dict()

        if run_id not in self._tree_map[subject_id][session_id][seq_id]:
            self._tree_map[subject_id][session_id][seq_id][run_id] = seq_info

    def __str__(self):
        """readable summary"""

        return "{} subjects with {} sessions in total" \
               "".format(len(self._tree_map), len(self._flat_map))

    def __repr__(self):
        return self.__str__()

    def _merge(self, other):
        """
        Merges two datasets.

        Parameters
        ----------
        other : BaseDataset
            Another instance of BaseDataset to merge with the current dataset


        .. note:: Note that the function will add all subjects, sessions, and
            runs from the *other* dataset
            to this dataset. This doesn't mean that *other* dataset will
            be equal to this dataset after the merge. But, this dataset
            will be a superset of the *other* dataset.
        """
        if not isinstance(other, BaseDataset):
            raise TypeError('Both must be a BaseDataset')

        if self.format != other.format:
            raise ValueError('Both must be of the same format')

        for seq_id in other.get_sequence_ids():
            for subj_id, sess_id, run_id, seq in other.traverse_horizontal(
                    seq_id):
                self.add(subject_id=subj_id, session_id=sess_id,
                         seq_id=seq_id, run_id=run_id, seq=seq)

    def merge(self, other):
        """
        Merges two datasets. This function is an alias for _merge(). It is
        provided for intuitive use. See _merge() for more details. It can be
        overloaded by the child classes to provide additional functionality.

        Parameters
        ----------
        other : BaseDataset
            Another instance of BaseDataset to merge with the current dataset
        """
        self._merge(other)

    def add(self, subject_id, session_id, seq_id, run_id, seq):
        """
        Adds a given sequence to provided subject_id, session_id and run_id for
        the dataset

        Parameters
        ----------
        subject_id : str
            Unique identifier for the Subject. For example, a subject ID can be
            a string like 'sub-01' or '001'.
        session_id : str
            Unique identifier the Session. For example, a session ID can be
            a string like 'ses-01' or '001'. For DICOM datasets, this can be
            StudyInstanceUID.
        seq_id : str
            Unique identifier the Sequence. For example, a sequence ID can be
            a string like 'fMRI' or 't1w'.
        run_id : str
            Unique identifier the Run. For example, a run ID can be
            a string like 'run-01' or '001'. For DICOM datasets, this can be
            SeriesInstanceUID.
        seq : protocol.BaseSequence
            Instance of the sequence
        """

        if not isinstance(seq, BaseSequence):
            raise TypeError(f'Expected BaseSequence but got {type(seq)}')

        if (subject_id, session_id, seq_id, run_id) not in self._flat_map:
            self._flat_map[(subject_id, session_id, seq_id, run_id)] = seq
            self._tree_add_node(subject_id=subject_id, session_id=session_id,
                                seq_id=seq_id, run_id=run_id, seq_info=seq)

            # map a sequence id to a specific runs with data for it
            if seq_id not in self._seqs_map:
                self._seqs_map[seq_id] = set()
            self._seqs_map[seq_id].add((subject_id, session_id, run_id))

            # maintaining a different cross-mappings for insight/debugging
            if session_id not in self._sess_map:
                self._sess_map[session_id] = set()
            self._sess_map[session_id].add(seq_id)

            # maintaining ID lists for easy reference
            self._subj_ids.add(subject_id)
            self._seq_ids.add(seq_id)

    def get(self, subject_id, session_id, seq_id, run_id, default=None):
        """
        Returns a Sequence given subject/session/seq/run from the dataset

        Parameters
        ----------
        subject_id : str
            Unique identifier for the Subject. For example, a subject ID can be
            a string like 'sub-01' or '001'.
        session_id : str
            Unique identifier the Session. For example, a session ID can be
            a string like 'ses-01' or '001'. For DICOM datasets, this can be
            StudyInstanceUID.
        seq_id : str
            Unique identifier the Sequence. For example, a sequence ID can be
            a string like 'fMRI' or 't1w'.
        run_id : str
            Unique identifier the Run. For example, a run ID can be
            a string like 'run-01' or '001'. For DICOM datasets, this can be
            SeriesInstanceUID.
        default : Any
            Default value to return if the sequence is not found
        """
        try:
            return self._tree_map[subject_id][session_id][seq_id][run_id]
        except KeyError:
            logger.info('Unable to find '
                        f'{subject_id}/{session_id}/{seq_id}/{run_id}')
            return default

    def __getitem__(self, subject_id):
        """intuitive getter"""
        return self._tree_map[subject_id]

    # def save(self, out_path=None):
    #     """offloads the data structure to disk for quicker reload"""
    #
    #     if out_path is None:
    #         out_path = self._saved_path
    #         out_path.parent.mkdir(exist_ok=True)
    #     else:
    #         if not out_path.parent.exists():
    #             try:
    #                 out_path.parent.mkdir(exist_ok=True)
    #             except Exception as exc:
    #                 print('out dir for the given path can not be created!')
    #                 raise exc
    #
    #     if len(self._subj_ids) >= 1:
    #         with open(out_path, 'wb') as out_file:
    #             pickle.dump(self, out_file)
    #     else:
    #         print('No subjects exist in the dataset. Not saving it!')

    def traverse_horizontal(self, seq_id):
        """
        Generator to traverse the dataset horizontally. i.e.,
        all subjects, across sessions and runs for a given sequence.
        The method will yield a tuple of (subject_id, session_id, run_id,
        sequence) for each sequence in the dataset.

        Parameters
        ----------
        seq_id : str
            Name of the Sequence ID

        Yields
        ------
        tuple_ids : tuple
            A tuple of subject_id, session_id, run_id, and protocol.Sequence
            instance
        """

        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                if seq_id in self._tree_map[subj][sess]:
                    for run in self._tree_map[subj][sess][seq_id]:
                        yield (subj, sess, run,
                               self._tree_map[subj][sess][seq_id][run])

    def traverse_vertical2(self, seq_id1, seq_id2):
        """
        Generator to traverse the dataset vertically. i.e.,
        sequences for a particular subject. The method will yield
        sequences from the same session for a given subject. For example,
        fMRI and associated field maps from the same session.

        Parameters
        ----------
        seq_id1 : str
            Name of the Sequence ID
        seq_id2 : str
            Name of the Sequence ID

        Yields
        ------
        tuple_ids : tuple
            A tuple of subj, sess, run, seq_one, seq_two
        """

        count = 0
        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                # checking for subset relationship
                if {seq_id1, seq_id2} <= self._tree_map[subj][sess].keys():
                    # two sequences may not have a common run ID
                    #   they might have multiple runs, with different number
                    #   of runs
                    #   so getting all of their linked combinations
                    linked_runs = self._link_runs_across_sequences(
                        self._tree_map[subj][sess][seq_id1],
                        self._tree_map[subj][sess][seq_id2])
                    for run1, run2 in linked_runs:
                        count = count + 1
                        yield (subj, sess, run1, run2,
                               self._tree_map[subj][sess][seq_id1][run1],
                               self._tree_map[subj][sess][seq_id2][run2])

        if count < 1:
            logger.info('There were no sessions/runs in these sequences!')

    def traverse_vertical_multi(self, *seq_ids):
        """
        Generator to traverse the dataset vertically. i.e.,
        sequences for a particular subject. The method will yield multiple
        sequences from the same session for a given subject. For example,
        fMRI, t1w and associated field maps from the same session.

        Parameters
        ----------
        seq_ids : list
            Sequence IDs to retrieve from the dataset

        Returns
        -------
        tuple_ids_data : tuple
            A tuple of subj, sess, tuple_runs, tuple_seqs
        """

        count = 0
        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                # if all seq IDs exist in session
                #   checking for subset relationship:
                if set(seq_ids) <= self._tree_map[subj][sess].keys():
                    seqs = [self._tree_map[subj][sess][sq] for sq in seq_ids]

                    # two sequences may not have a common run ID
                    #   they might have multiple runs, with different number
                    #   of runs
                    #   so getting all of their linked combinations
                    runs = self._first_run_from_sequences(seqs)

                    out_seqs = [self._tree_map[subj][sess][seq_id][run_id]
                                for seq_id, run_id in zip(seq_ids, runs)]

                    count = count + 1
                    yield subj, sess, runs, out_seqs

        if count < 1:
            logger.warning(
                f'There were no sessions with all {len(seq_ids)} '
                'input sequences!')

    @staticmethod
    def _first_run_from_sequences(seq_list):
        """returns the first run from each of the input sequences"""

        # picking the first run from each sequence
        run_list = list()
        for seq in seq_list:
            if len(seq.keys()) >= 1:
                # print(f'{seq} has more than 1 run! choosing the first')
                first_run = list(seq.keys())[0]
                run_list.append(first_run)
            else:
                logger.warning(f'skipping {seq} with no runs!')

        return run_list

    # @staticmethod
    # def _run_combinations_across_sequences(seq_list):
    #     """returns a combinatorial pairs of runs from sequence list"""
    #
    #     run_lists = [list(seq.keys()) for seq in seq_list if
    #                  len(seq.keys()) >= 1]
    #
    #     for ii in range(len(run_lists)):
    #         # remaining lists
    #         for jj in range(ii + 1, len(run_lists)):
    #             # for each element from first list
    #             for kk in range(len(run_lists[ii])):
    #                 # all elements from the other lists
    #                 for qq in range(len(run_lists[jj])):
    #                     yield run_lists[ii][kk], run_lists[jj][qq]
    #
    #     return run_lists

    @staticmethod
    def _link_runs_across_sequences(seq_dict1, seq_dict2):
        """returns a combinatorial combination of runs from two sequences"""

        # no need to compute set() on dict key() as they are already unique
        if len(seq_dict1.keys()) < 1:
            logger.warning(f'{seq_dict1} has no runs!')

        if len(seq_dict2.keys()) < 1:
            logger.warning(f'{seq_dict2} has no runs!')

        # combinatorial
        for run_one, run_two in product(seq_dict1.keys(), seq_dict2.keys()):
            yield run_one, run_two

    def __eq__(self, other):
        """equality check"""

        if not isinstance(other, BaseDataset):
            raise TypeError('Both must be a BaseDataset')

        if self.format != other.format:
            raise ValueError('Both must be of the same format')

        if self._flat_map == other._flat_map:
            return True
        else:
            return False
