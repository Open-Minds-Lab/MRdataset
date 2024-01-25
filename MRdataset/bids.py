from abc import ABC
from pathlib import Path

from protocol import BidsImagingSequence

from MRdataset import logger
from MRdataset.base import BaseDataset
from MRdataset.config import VALID_BIDS_DATATYPES
from MRdataset.dicom_utils import is_bids_file
from MRdataset.utils import folders_with_min_files, valid_dirs


class BidsDataset(BaseDataset, ABC):
    """Class to represent a BIDS dataset"""

    def __init__(self, data_source, pattern="*.json",
                 name='BidsDataset',
                 config_path=None,
                 verbose=False,
                 ds_format='bids',
                 output_dir=None,
                 **kwargs):
        super().__init__(data_source=data_source, name=name, ds_format=ds_format)
        self.data_source = valid_dirs(data_source)
        self.pattern = pattern
        self.config_path = config_path
        self.verbose = verbose
        self.config_dict = None
        self.min_count = 1

        try:
            self.output_dir = Path(output_dir)
        except TypeError as exc:
            logger.error('Output directory not valid. Got: {output_dir}')
            raise exc

        self.output_dir.mkdir(exist_ok=True, parents=True)

    def load(self):
        for directory in self.data_source:
            subfolders = folders_with_min_files(directory, self.pattern,
                                                 self.min_count)
            for folder in subfolders:
                sequences = self._process(folder)
                for seq in sequences:
                    self.add(subject_id=seq.subject_id,
                             session_id=seq.session_id,
                             run_id=seq.run_id,
                             seq_id=seq.name, seq=seq)

    def _filter_json_files(self, folder):
        json_files = sorted(folder.glob(self.pattern))
        valid_bids_files = filter(is_bids_file, json_files)
        if not valid_bids_files:
            logger.info(f'No valid BIDS files found in {folder}')
            return []
        return valid_bids_files

    def _process(self, folder):
        json_files = self._filter_json_files(folder)
        sequences = []
        for i, file in enumerate(json_files):
            seq = BidsImagingSequence(bidsfile=file, path=folder)
            name = file.parent.name
            if name not in VALID_BIDS_DATATYPES:
                logger.info(f'Invalid datatype found: {name}. Skipping it')
                return
            subject_id = file.parents[2].name
            session_id = file.parents[1].name
            if 'sub' in session_id:
                logger.info(f"Sessions don't exist: {session_id}.")
                subject_id = session_id
                session_id = 'ses-01'
            # None of the datasets we processed (over 20) had run information,
            # even though BIDS allows it. So we just use run-0x for all of them.
            run_id = f'run-{str(i+1).zfill(2)}'
            seq.set_session_info(subject_id=subject_id,
                                 session_id=session_id,
                                 run_id=run_id,
                                 name=name)
            if seq.is_valid():
                sequences.append(seq)
        return sequences

