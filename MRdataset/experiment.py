import pickle
from abc import ABC, abstractmethod
from collections import UserDict
from pathlib import Path
from warnings import warn

from protocol import ImagingSequence
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from MRdataset.dicom_utils import (get_metadata, is_valid_inclusion)
from MRdataset.utils import folders_with_min_files


# A dataset is a collection of subjects
# A subject is a collection of sessions
# A session is a collection of runs
# A run is one instance of a sequence;
# A sequence can have multiple runs in a session
# A sequence is a collection of parameters
#
# related useful references
#   https://bids-specification.readthedocs.io/en/stable/appendices/entities.html
#
# dicom2nifti logic for naming files:
# https://github.com/icometrix/dicom2nifti/blob/ecbf43a66174375285fae485439ea8dd940005ba/dicom2nifti/convert_dir.py#L68
#

class Run(UserDict):
    """Container for an imaging run.

    Design:
    - A run is an instance of a sequence
    - A session can have multiple runs acquired with the same sequence/parameters
    - for only a SINGLE subject

    """


    def __init__(self,
                 session_id: str = 'SessionID',
                 subject_id: str = 'SubjectID',
                 sequence: ImagingSequence = None):
        """constructor"""

        super().__init__()
        self.session_id = session_id
        self.subject_id = subject_id
        self.sequence = sequence


class Session(UserDict):
    """Container for an imaging session.

    Design:
    - A session is a collection of runs,
        and each run is different acquisition with the same sequence/parameters
    - for only a SINGLE subject
    - like a Visit in longitudinal studies
    """


    def __init__(self,
                 session_id='SessionID',
                 subject_id='SubjectID',
                 runs: list[Run] = None):
        """constructor"""

        super().__init__()
        self.session_id = session_id
        self.subject_id = subject_id
        self.runs = runs


class Subject(UserDict):
    """base class for all subjects"""


    def __init__(self,
                 subject_id='SubjectID',
                 sessions: list[Session] = None):
        """constructor"""

        super().__init__()
        self.subject_id = subject_id
        self.sessions = sessions


class BaseDataset(ABC):
    """base class for all MR datasets"""


    def __init__(self,
                 root,
                 name: str = 'Dataset',
                 format: str = 'DICOM',
                 subjects: list[Subject] = None):
        """constructor"""

        fp = Path(root).resolve()
        if fp.exists():
            self.root = fp
        else:
            raise IOError('Root folder for {} does not exist at {}'
                          ''.format(name, fp))

        self.name = name
        self.format = format

        self.subjects = subjects
        self._subj_ids = set()
        self._seq_ids = set()

        self._tree_map = dict()
        self._flat_map = dict()

        self._seqs_map = dict()
        self._sess_map = dict()

        self._saved_path = self.root / "mrdataset" / "mrdataset.pkl"
        self._reloaded = False

        self._key_vars = set(['_flat_map',  # noqa
                              '_tree_map',
                              '_subj_ids',
                              '_seq_ids',
                              'format',
                              'name',
                              'root',
                              'subjects'])


    def _reload_saved(self):
        """helper to reload previously saved MRdataset"""

        if len(self._subj_ids) > 0 and self._reloaded:
            print('Dataset seems to be loaded already. Skipping reload!')

        try:
            print('reloading previously parsed MRdataset ...')
            with open(self._saved_path, 'rb') as in_file:
                prev = pickle.load(in_file)
            for attr in self._key_vars:
                self.__setattr__(attr, getattr(prev, attr))
        except Exception as exc:
            print(f'unable to reload from {self._saved_path}')
            raise exc
        else:
            self._reloaded = True
            print(self)


    @abstractmethod
    def load(self):
        """default method to load the dataset"""


    def _tree_add_node(self, subject_id, session_id, run_id, seq_name, seq_info):
        """helper to add nodes deep in the tree

        hierarchy: Subject > Session > Sequence > Run

        """

        if subject_id not in self._tree_map:
            self._tree_map[subject_id] = dict()

        if session_id not in self._tree_map[subject_id]:
            self._tree_map[subject_id][session_id] = dict()

        if seq_name not in self._tree_map[subject_id][session_id]:
            self._tree_map[subject_id][session_id][seq_name] = dict()

        self._tree_map[subject_id][session_id][seq_name][run_id] = seq_info


    def __str__(self):
        """readable summary"""

        return "{} subjects with {} sessions in total" \
               "".format(len(self._tree_map), len(self._flat_map))


    def __repr__(self):
        return self.__str__()


    def add(self, subject_id, session_id, run_id, seq_id, seq):
        """adds a given subject, session or run to the dataset"""

        if (subject_id, session_id, run_id, seq_id) not in self._flat_map:
            self._flat_map[(subject_id, session_id, run_id, seq_id)] = seq
            self._tree_add_node(subject_id, session_id, run_id, seq_id, seq)

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


    def get(self, subject_id, session_id, run_id, seq_id):
        """returns a given subject/session/seq/run from the dataset"""

        return self._tree_map[subject_id][session_id][seq_id][run_id]


    def __getitem__(self, subject_id):
        """intuitive getter"""

        return self._tree_map[subject_id]


    def save(self, out_path=None):
        """offloads the data structure to disk for quicker reload"""

        if out_path is None:
            out_path = self._saved_path
            out_path.parent.mkdir(exist_ok=True)
        else:
            if not out_path.parent.exists():
                try:
                    out_path.parent.mkdir(exist_ok=True)
                except Exception as exc:
                    print('out dir for the given path can not be created!')
                    raise exc

        if len(self._subj_ids) >= 1:
            with open(out_path, 'wb') as out_file:
                pickle.dump(self, out_file)
        else:
            print('No subjects exist in the dataset. Not saving it!')


    def traverse_horizontal(self, seq_id):
        """method to traverse the dataset horizontally
            i.e., same sequence, across subjects
        """

        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                if seq_id in self._tree_map[subj][sess]:
                    for run in self._tree_map[subj][sess][seq_id]:
                        yield (subj, sess, run,
                               self._tree_map[subj][sess][seq_id][run])


    def traverse_vertical2(self, seq_one, seq_two):
        """
         method to traverse the dataset horizontally
            i.e., within subject, across sequences


        Returns
        -------
        tuple_ids_data : tuple
            tuple of subj, sess, run, seq_one, seq_two
        """

        count = 0
        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                # checking for subset relationship
                if {seq_one, seq_two} <= self._tree_map[subj][sess].keys():
                    # two sequences may not have a common run ID
                    #   they might have multiple runs, with different number of runs
                    #   so getting all of their linked combinations
                    linked_runs = self._link_runs_across_sequences(
                        self._tree_map[subj][sess][seq_one],
                        self._tree_map[subj][sess][seq_two])
                    for run_one, run_two in linked_runs:
                        count = count + 1
                        yield (subj, sess, run_one, run_two,
                               self._tree_map[subj][sess][seq_one][run_one],
                               self._tree_map[subj][sess][seq_two][run_two])

        if count < 1:
            print('There were no sessions/runs with both these sequences!')


    def traverse_vertical_multi(self, *seq_ids):
        """
         method to traverse the dataset horizontally
            i.e., within subject, across sequences


        Returns
        -------
        tuple_ids_data : tuple
            tuple of subj, sess, tuple_runs, tuple_seqs
        """

        count = 0
        for subj in self._subj_ids:
            for sess in self._tree_map[subj]:
                # if all seq IDs exist in session
                #   checking for subset relationship:
                if set(seq_ids) <= self._tree_map[subj][sess].keys():

                    seqs = [self._tree_map[subj][sess][sq] for sq in seq_ids]

                    # two sequences may not have a common run ID
                    #   they might have multiple runs, with different number of runs
                    #   so getting all of their linked combinations
                    runs = self._first_run_from_sequences(seqs)

                    out_seqs = [self._tree_map[subj][sess][ss][rr]
                                for rr, ss in zip(runs, seq_ids)]

                    count = count + 1
                    yield subj, sess, runs, out_seqs

        if count < 1:
            print(f'There were no sessions with all {len(seq_ids)} input sequences!')


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
                print(f'skipping {seq} with no runs!')

        return run_list


    @staticmethod
    def _run_combinations_across_sequences(seq_list):
        """returns a combinatorial pairs of runs from sequence list"""

        run_lists = [list(seq.key()) for seq in seq_list if len(seq.keys()) >= 1]

        for ii in range(len(run_lists)):
            # remaining lists
            for jj in range(ii+1, len(run_lists)):
                # for each element from first list
                for kk in range(len(run_lists[ii])):
                    # all elements from the other lists
                    for qq in range(len(run_lists[jj])):
                        yield run_lists[ii][kk], run_lists[jj][qq]

        return run_lists


    @staticmethod
    def _link_runs_across_sequences(seq_one, seq_two):
        """returns a combinatorial combination of runs from two sequences"""

        # no need to compute set() on dict key() as they are already unique
        if len(seq_one.keys()) < 1:
            print(f'{seq_one} has no runs!')

        if len(seq_two.keys()) < 1:
            print(f'{seq_two} has no runs!')

        # combinatorial
        for run_one in seq_one.keys():
            for run_two in seq_two.keys():
                yield run_one, run_two


class DicomDataset(BaseDataset, ABC):
    """Class to represent a DICOM dataset"""


    def __init__(self,
                 root,
                 pattern="*.dcm",
                 name='DicomDataset',
                 include_phantoms=False):
        """constructor"""

        super().__init__(root=root, name=name, format='DICOM')

        self.include_phantoms = include_phantoms
        self.pattern = pattern
        self.min_count = 3  # min slice count to be considered a volume

        # variables specific to this class
        self._key_vars.update(['pattern', 'min_count', 'include_phantoms'])

        if self._saved_path.exists():
            self._reload_saved()

        print('')


    def load(self, refresh=False):
        """default method to load the dataset"""

        if self._saved_path.exists() and not refresh:
            self._reload_saved()
            return

        sub_folders = folders_with_min_files(self.root, self.pattern, self.min_count)

        for folder in sub_folders:
            try:
                seq_name, seq_info, subject_id, session_id, run_id = \
                    self._process_slice_collection(folder)
            except:
                print(f'Unable to process {folder}. Skipping it.')
            else:
                self.add(subject_id, session_id, run_id, seq_name, seq_info)
                print(f'adding {subject_id} session {session_id:80} -- {seq_name}')

        # saving a copy for quicker reload
        self.save()


    def _process_slice_collection(self, folder):
        """reads the dicom slices and runs some basic validation on them!"""

        # within a folder, a volume can be multi-echo, so we must read them all
        #   and find a way to capture

        dcm_files = sorted(folder.glob(self.pattern))

        if len(dcm_files) < 1:
            warn(f'no files matching the pattern {self.pattern} found in {folder}',
                 UserWarning)

        # run some basic validation of these dcm slice collection
        #   SeriesInstanceUID must match
        #   parameter values must match, except echo time

        non_compl = list()
        for idx, dcm_path in enumerate(dcm_files):

            try:
                dicom = dcmread(dcm_path, stop_before_pixels=True)
            except InvalidDicomError as ide:
                print(f'Invalid DICOM file at {dcm_path}')
                continue

            if not is_valid_inclusion(dcm_path, dicom, self.include_phantoms):
                continue

            seq_name, subject_id, session_id, run_name = get_metadata(dicom)

            if idx == 0:
                first_slice = ImagingSequence(dicom=dicom, name=f'{seq_name}')
            else:
                cur_slice = ImagingSequence(dicom=dicom, name=f'{seq_name}')

                if not cur_slice == first_slice:  # noqa
                    non_compl.append(cur_slice)

        first_slice.multi_echo = False
        if len(non_compl) > 1:
            echo_times = set()
            echo_times.add(first_slice['EchoTime'].value)
            for ncs in non_compl:
                echo_times.add(ncs['EchoTime'].value)
            if len(echo_times) > 1:
                first_slice.multi_echo = True

        return seq_name, first_slice, subject_id, session_id, run_name  # noqa
