from typing import Optional

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
                 config_path=None,
                 verbose=False,
                 **kwargs):
        """constructor"""

        super().__init__(data_source=data_source, name=name, ds_format='DICOM')
        self.data_source = valid_dirs(data_source)
        self.pattern = pattern
        self.min_count = 1  # min slice count to be considered a volume
        self.verbose = verbose
        self.config_path = config_path
        self.config_dict = None

        # read the config file
        try:
            self.config_dict = read_json(self.config_path)
        except (FileNotFoundError or ValueError) as e:
            logger.error(f'Unable to read config file {self.config_path}')
            raise e

        # Whether to use echo numbers to identify multi-echo sequences
        self.use_echo_numbers = self.config_dict.get('use_echonumbers',
                                                     False)
        # These parameters will be checked for compliance
        self.imaging_params = self.config_dict['include_parameters']

        # These are used to skip certain sequences
        self.includes = self.config_dict.get('include_sequence', {})
        self.include_phantom = self.includes.get('phantom', None)
        self.include_moco = self.config_dict.get('moco', None)
        self.include_sbref = self.config_dict.get('sbref', None)

        # variables specific to this class
        self._key_vars.update(['pattern', 'min_count', 'include_phantoms'])

        # these are the required parameters for internal purposes. But these
        #  will not be checked for compliance
        self._required_params = ['EchoTime', 'EchoNumber', 'Manufacturer',
                                 'ContentDate', 'ContentTime']

        # if self._saved_path.exists():
        #     self._reload_saved()

        # print('')

    def load(self, refresh=False):
        """
        default method to load the dataset. This method is called by import_dataset function. Any
        dataset_type must implement this method.
        """

        # if self._saved_path.exists() and not refresh:
        #     self._reload_saved()
        #     return

        for directory in self.data_source:
            # find all the sub-folders with at least min_count files
            sub_folders = folders_with_min_files(directory, self.pattern,
                                                 self.min_count)
            if not sub_folders:
                logger.warn(f'No folders with at least {self.min_count} '
                            f'files found in {directory}. Skipping it.')
                continue
            if self.verbose:
                # Puts a nice progress bar, but slows down the process
                sub_folders = tqdm(list(sub_folders))

            for folder in sub_folders:
                # process each folder
                seq = self._process_slice_collection(folder)
                if seq is None:
                    logger.info(f'Unable to process {folder}. Skipping it.')
                else:
                    self.add(seq.subject_id, seq.session_id,
                             seq.run_id, seq.name, seq)

        # saving a copy for quicker reload
        # self.save()

    def _process_slice_collection(self, folder):
        """reads the dicom slices and runs some basic validation on them!"""

        # within a folder, a volume can be multi-echo, so we must read them all
        #   and find a way to capture the echo time information
        dcm_files = sorted(folder.glob(self.pattern))

        # if no files found, return None
        if len(dcm_files) < self.min_count:
            logger.warn(
                f'no files matching the pattern {self.pattern} found in {folder}',
                UserWarning)
            return None

        # run some basic validation of these dcm slice collection
        #   session_info must match
        #   parameter values must also match in general

        # However, for certain sequences, the parameter may vary
        #   (e.g. EchoTime for multi-echo). Therefore, we need to
        #   find a way to capture the varying parameters. We collect
        #   all the slices and then process them to find the varying
        #   parameters.

        # collect all the slices with diverging parameters
        divergent_slices = list()
        first_slice = None
        for idx, dcm_path in enumerate(dcm_files):
            # check if it is a valid dicom file
            if not is_dicom_file(dcm_path):
                continue

            try:
                dicom = dcmread(dcm_path, stop_before_pixels=True)
            except InvalidDicomError:
                logger.info(f'Invalid DICOM file at {dcm_path}')
                continue

            # skip localizer, phantom, scouts, sbref, etc
            if not is_valid_inclusion(dicom, self.include_phantom):
                continue

            if idx == 0:
                first_slice = ImagingSequence(
                    dicom=dicom,
                    imaging_params=self.imaging_params,
                    required_params=self._required_params,
                    path=folder
                )
                # We collect the first slice as a reference to compare
                #   other slices with
                divergent_slices.append(first_slice)

            else:
                cur_slice = ImagingSequence(
                    dicom=dicom,
                    imaging_params=self.imaging_params,
                    required_params=self._required_params,
                    path=folder)

                # check if the session info is same
                # Session info includes subject_id, session_id, run_id
                if cur_slice.get_session_info() != first_slice.get_session_info():
                    logger.warn(f'Inconsistent session info for {dcm_path}')
                    continue

                # check if the parameters are same with the slices
                #   collected so far
                for sl in divergent_slices:
                    if cur_slice != sl:
                        divergent_slices.append(cur_slice)

        if len(divergent_slices) > 1:
            # if there are divergent slices, we need to process them
            #   to find the varying parameters. For now we just look for echo-time
            #   and echo-number, but we can extend this to other parameters such as
            #   flip-angle, etc.
            echo_times, echo_nums = self._process_echo_times(divergent_slices)
            first_slice.set_echo_times(echo_times, echo_nums)
        return first_slice

    def _process_echo_times(self, divergent_slices: list) -> tuple(list, Optional[list]):
        """
        Finds the set of echo times and echo numbers from the list of
        slices. However, the echo number is not always available
        in the dicom header. In that case, we may have to look for a unique
        set of echo times. Although this is not preferred, but we can use this.

        Parameters
        ----------
        divergent_slices : list
            ImagingSequence objects with divergent parameters

        Returns
        -------
        echo_times : list
            collected list of echo times
        echo_nums : Optional[List]
            collected list of echo numbers

        """
        if self.use_echo_numbers:
            echo_dict = dict()
            for sl in divergent_slices:
                enum = sl['EchoNumber'].value
                if enum not in echo_dict:
                    echo_dict[enum] = sl['EchoTime'].value
            return echo_dict.values(), echo_dict.keys()
        else:
            echo_times = set()
            for sl in divergent_slices:
                echo_times.add(sl['EchoTime'].value)
            return echo_times, None
