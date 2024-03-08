from abc import ABC
from pathlib import Path
from re import search

from MRdataset import logger
from MRdataset.base import BaseDataset
from MRdataset.config import VALID_BIDS_DATATYPES, SUPPORTED_BIDS_DATATYPES
from MRdataset.dicom_utils import is_bids_file
from MRdataset.utils import folders_with_min_files, valid_dirs, read_json
from protocol import BidsImagingSequence


class BidsDataset(BaseDataset, ABC):
    """
    Class to represent a BIDS dataset. It is a subclass of BaseDataset.
    It gathers data from JSON files.

    Parameters
    ----------
    data_source : str or List[str]
        The path to the dataset.
    pattern : str
        The pattern to match for JSON files.
    name : str
        The name of the dataset.
    config_path : str
        The path to the config file.
    verbose : bool
        Whether to print verbose output on console.
    ds_format : str
        The format of the dataset. One of ['dicom', 'bids'].
    """

    def __init__(self, data_source, pattern="*.json",
                 name='BidsDataset',
                 config_path=None,
                 verbose=False,
                 output_dir=None,
                 min_count=1,
                 **kwargs):

        super().__init__(data_source=data_source, name=name, ds_format='bids')
        self.data_source = valid_dirs(data_source)
        self.pattern = pattern
        self.config_path = config_path
        self.verbose = verbose
        self.config_dict = None
        self.min_count = min_count

        try:
            self.output_dir = Path(output_dir)
        except TypeError as exc:
            logger.error('Output directory not valid. Got: {output_dir}')
            raise exc

        self.output_dir.mkdir(exist_ok=True, parents=True)

        # read the config file
        try:
            self.config_dict = read_json(Path(self.config_path))
        except (FileNotFoundError, ValueError) as e:
            logger.error(f'Unable to read config file {self.config_path}')
            raise e

        self.includes = self.config_dict.get('include_sequence', {})
        self.include_nifti_headers = self.includes.get('nifti_header', False)

    def load(self):
        """
        Default method to load the dataset. It iterates over all the folders
        in the data_source and finds subfolders with at least min_count files
        matching the pattern. It then processes each subfolder and adds the
        sequence to the dataset.
        """

        for directory in self.data_source:
            # find all sub-folders with at least min_count files matching the
            # pattern
            subfolders = folders_with_min_files(directory, self.pattern,
                                                self.min_count)
            for folder in subfolders:
                # process each folder
                sequences = self._process(folder)
                for seq in sequences:
                    self.add(subject_id=seq.subject_id,
                             session_id=seq.session_id,
                             run_id=seq.run_id,
                             seq_id=seq.name, seq=seq)

    def _filter_json_files(self, folder):
        """Filters the JSON files from the folder."""
        json_files = sorted(folder.glob(self.pattern))
        valid_bids_files = list(filter(is_bids_file, json_files))
        if not valid_bids_files:
            logger.info(f'No valid BIDS files found in {folder}')
            return []
        return valid_bids_files

    def _process(self, folder):
        """Processes the folder and returns a list of sequences."""
        json_files = self._filter_json_files(folder)
        sequences = []
        last_id = 0
        for i, file in enumerate(json_files):
            try:
                seq = BidsImagingSequence(bidsfile=file, path=folder)
            except (ValueError, IOError) as exc:
                logger.error(f'Error processing {file}. Skipping it. Got {exc}')
                continue

            name = file.parent.name
            if name not in VALID_BIDS_DATATYPES:
                logger.error(f'Invalid datatype found: {name}. Skipping it')
                return sequences

            subject_id = file.parents[2].name
            session_id = file.parents[1].name
            if 'sub' in session_id:
                logger.info(f"Sessions don't exist: {session_id}.")
                subject_id = session_id
                session_id = 'ses-01'

            # None of the datasets we processed (over 20) had run information,
            # even though BIDS allows it. So we just use run-0x for all of them.
            run_id, last_id = self.get_run_id(file, last_id)
            seq.set_session_info(subject_id=subject_id,
                                 session_id=session_id,
                                 run_id=run_id,
                                 name=name)
            if seq.is_valid():
                sequences.append(seq)
            else:
                if name not in SUPPORTED_BIDS_DATATYPES:
                    logger.warning(f'MRdataset primarily supports '
                                   f'{SUPPORTED_BIDS_DATATYPES} .'
                                   f'It seems the parameters in '
                                   f'this sequence are invalid or '
                                   f'not supported yet. Skipping it.')
        return sequences

    @staticmethod
    def get_run_id(filename, last_id):
        """
        Use regex to extract run id from filename.
        Example filename : sub-01_ses-imagery01_task-imagery_run-01_bold.json
        """
        # Regular expression pattern
        pattern = r'run-[^_]+'
        # Extracting substring using regex
        match = search(pattern, str(filename))

        if match:
            run_id = match.group(0)
            new_id_num = int(run_id.split('-')[-1])
        else:
            new_id_num = last_id + 1
            run_id = f'run-{str(new_id_num).zfill(2)}'
        return run_id, new_id_num
