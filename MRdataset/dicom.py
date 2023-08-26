from tqdm import tqdm
from abc import ABC

from protocol import ImagingSequence
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from MRdataset.base import BaseDataset
from MRdataset import logger
from MRdataset.dicom_utils import (extract_session_info, is_valid_inclusion,
                                   is_dicom_file)
from MRdataset.utils import (folders_with_min_files, read_json, valid_dirs)


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
# https://github.com/icometrix/dicom2nifti/blob
# /ecbf43a66174375285fae485439ea8dd940005ba/dicom2nifti/convert_dir.py#L68
#


class DicomDataset(BaseDataset, ABC):
    """Class to represent a DICOM dataset"""

    def __init__(self,
                 data_source,
                 pattern="*",
                 name='DicomDataset',
                 include_phantom=False,
                 config_path=None,
                 **kwargs):
        """constructor"""

        super().__init__(data_source=data_source, name=name, ds_format='DICOM')
        self.data_source = valid_dirs(data_source)
        self.include_phantom = include_phantom
        self.pattern = pattern
        self.min_count = 1  # min slice count to be considered a volume

        self.config_path = config_path
        self.config_dict = None
        self.use_echo_numbers = True

        try:
            self.config_dict = read_json(self.config_path)
        except (FileNotFoundError or ValueError) as e:
            logger.error(f'Unable to read config file {self.config_path}')
            raise e

        self.imaging_params = self.config_dict['include_parameters']

        # variables specific to this class
        self._key_vars.update(['pattern', 'min_count', 'include_phantoms'])
        self._required_params = ['EchoTime', 'EchoNumber']

        # if self._saved_path.exists():
        #     self._reload_saved()

        # print('')

    def load(self, refresh=False):
        """default method to load the dataset"""

        # if self._saved_path.exists() and not refresh:
        #     self._reload_saved()
        #     return

        for directory in self.data_source:
            sub_folders = folders_with_min_files(directory, self.pattern,
                                                 self.min_count)
            sub_folders = list(sub_folders)
            for folder in tqdm(sub_folders):
                metadata = None
                metadata = self._process_slice_collection(folder)
                if metadata is None:
                    logger.info(f'Unable to process {folder}. Skipping it.')
                else:
                    seq_name, seq_info, subject_id, session_id, run_id = metadata
                    self.add(subject_id, session_id, run_id, seq_name, seq_info)

        # saving a copy for quicker reload
        # self.save()

    def _process_slice_collection(self, folder):
        """reads the dicom slices and runs some basic validation on them!"""

        # within a folder, a volume can be multi-echo, so we must read them all
        #   and find a way to capture

        dcm_files = sorted(folder.glob(self.pattern))

        if len(dcm_files) < 1:
            logger.warn(
                f'no files matching the pattern {self.pattern} found in {folder}',
                UserWarning)

        # run some basic validation of these dcm slice collection
        #   SeriesInstanceUID must match
        #   parameter values must match, except echo time

        non_compliant = list()
        first_slice = None
        for idx, dcm_path in enumerate(dcm_files):
            if not is_dicom_file(dcm_path):
                continue

            try:
                dicom = dcmread(dcm_path, stop_before_pixels=True)
            except InvalidDicomError:
                logger.info(f'Invalid DICOM file at {dcm_path}')
                continue

            if not is_valid_inclusion(dcm_path, dicom, self.include_phantom):
                continue

            seq_name, subject_id, session_id, run_id = extract_session_info(
                dicom)  # noqa

            if idx == 0:
                first_slice = ImagingSequence(
                    dicom=dicom, name=f'{seq_name}',
                    imaging_params=self.imaging_params,
                    required_params=self._required_params,
                    path=folder
                )
                non_compliant.append(first_slice)
                first_slice.set_session_info(subject_id, session_id, run_id)

            else:
                cur_slice = ImagingSequence(
                    dicom=dicom, name=f'{seq_name}',
                    imaging_params=self.imaging_params,
                    required_params=self._required_params,
                    path=folder)
                cur_slice.set_session_info(subject_id, session_id, run_id)

                if cur_slice.get_session_info() != first_slice.get_session_info():
                    logger.warn(f'Inconsistent session info for {dcm_path}')
                    continue

                if all(cur_slice != slice for slice in non_compliant):  # noqa
                    non_compliant.append(cur_slice)

        if len(non_compliant) > 0:
            if self.use_echo_numbers:
                echo_dict = dict()
                for sl in non_compliant:
                    enum = sl['EchoNumber'].value
                    if enum not in echo_dict:
                        echo_dict[enum] = sl['EchoTime'].value
                first_slice.set_echo_times(echo_dict.values(), echo_dict.keys())
            else:
                echo_times = set()
                for ncs in non_compliant:
                    echo_times.add(ncs['EchoTime'].value)
                first_slice.set_echo_times(echo_times, None)
            return seq_name, first_slice, subject_id, session_id, run_id  # noqa
        return None
