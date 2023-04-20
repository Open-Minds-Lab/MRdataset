from pathlib import Path

import pydicom

from MRdataset import config
from MRdataset.base import BaseDataset, Run, Modality, Subject, Session
from MRdataset.dicom_utils import is_dicom_file, is_valid_inclusion, \
    get_dicom_modality_tag, is_same_set, parse_imaging_params, \
    combine_varying_params
from MRdataset.log import logger
from MRdataset.utils import param_difference, files_in_path
from MRdataset.config import DatasetEmptyException

# Module-level logger
# logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class DicomDataset(BaseDataset):
    """
    Container to manage properties and issues of a dataset downloaded from
    XNAT. Expects the data_source to be collection of dicom files, which may
    belong to different subjects, modalities, sessions or runs.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    data_source : Path or str or Iterable
        directories containing dicom files, supports nested hierarchies
    include_phantom
        Whether to include non-subject scans like localizer, acr/phantom,
        head_scout
    """

    def __init__(self,
                 data_source=None,
                 include_phantom=False,
                 is_complete=True,
                 name=None,
                 **_kwargs):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_source : Path or str or Iterable
            directory containing dicom files, supports nested hierarchies
        include_phantom : bool
            whether to include localizer/aahead_scout/phantom/acr
        is_complete : bool
            whether the dataset is complete or partial (default: True)


        Examples
        --------
        >>> from MRdataset import dicom
        >>> dataset = dicom.DicomDataset()
        """
        super().__init__(data_source)
        self.is_complete = is_complete
        self.include_phantom = include_phantom
        self.name = name

    def walk(self):
        """
        Retrieves filenames in the directory tree, verifies if it is dicom
        file, extracts relevant parameters and stores it in project. Creates
        a desirable hierarchy for a neuroimaging experiment
        """
        no_files_found = True
        study_ids_found = set()

        for filepath in files_in_path(self.data_source):
            no_files_found = False
            try:
                if not is_dicom_file(filepath):
                    logger.debug(
                        "Not a DICOM file : {}".format(filepath))
                    continue
                # TODO: Read dicom file : 2
                dicom = pydicom.read_file(filepath, stop_before_pixels=True)
                if is_valid_inclusion(filepath,
                                      dicom,
                                      self.include_phantom):

                    modality_name = get_dicom_modality_tag(dicom)
                    modality_obj = self.get_modality_by_name(modality_name)
                    if modality_obj is None:
                        modality_obj = Modality(modality_name)

                    patient_id = str(dicom.get('PatientID', None))
                    subject_obj = modality_obj.get_subject_by_name(patient_id)
                    if subject_obj is None:
                        subject_obj = Subject(patient_id)

                    series_num = str(dicom.get('SeriesNumber', None))
                    session_node = subject_obj.get_session_by_name(series_num)
                    if session_node is None:
                        session_node = Session(series_num)

                    run_name = is_same_set(dicom)
                    run_node = session_node.get_run_by_name(run_name)
                    # Cast as int as sometime it may return a MultiValue type
                    # TODO: check Rembrandt dataset
                    try:
                        echo_numbers = int(dicom.get('EchoNumbers', None))
                    except TypeError as e:
                        echo_numbers = 1
                        logger.warning(f'Got {e}')

                    if run_node is None:
                        run_node = Run(run_name)
                        # Create bins for each echo time. If echo numbers
                        # is 1, then it is a single echo time, so we put all
                        # runs to default bin with echo time 1.0. This will not
                        # affect the echo times on the report. And, if echo
                        # numbers is greater than 1, then we create bins for
                        # each differing echo time. Even though the variable
                        # name is inconsistent, it is not a bug. Trying to make
                        # as minimal changes as possible.
                        # TODO: use array type instead of single value for echo
                        #  time
                        if echo_numbers > 1:
                            run_node.echo_time = dicom.get('EchoTime', 1.0)
                        else:
                            run_node.echo_time = 1.0
                    # TODO: dcm_img_params doesnt make sense
                    dcm_img_params = parse_imaging_params(filepath)
                    param_diff = param_difference(dcm_img_params,
                                                  run_node.params)
                    if len(run_node.params) == 0:
                        run_node.params = dcm_img_params.copy()
                    elif param_diff:
                        run_node.params = combine_varying_params(
                                            param_diff,
                                            run_node.params,
                                            filepath)
                    session_node.add_run(run_node)
                    subject_obj.add_session(session_node)
                    modality_obj.add_subject(subject_obj)
                    self.add_modality(modality_obj)

                    # Collect all unique study ids found in DICOM
                    study_ids_found.add(str(dicom.StudyID))

            except config.MRException as mrd_exc:
                logger.exception(mrd_exc)
            except PermissionError as e:
                logger.error(e)
            except Exception as exc:
                raise exc
        if no_files_found:
            raise DatasetEmptyException()
        if len(study_ids_found) > 1:
            logger.warning(config.MultipleProjectsInDataset(study_ids_found))
