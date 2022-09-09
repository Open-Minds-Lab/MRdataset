import logging
from pathlib import Path

import dicom2nifti
import pydicom
from MRdataset import common_dicom
from MRdataset import config
from MRdataset.base import Project, Run, Modality, Subject, Session
from MRdataset.utils import param_difference, files_under_folder

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class XnatDataset(Project):
    """
    Container to manage properties and issues of a dataset downloaded from
    XNAT. Expects the data_root to be collection of dicom files, which may
    belong to different subjects, modalities, sessions or runs.

    Attributes
    ----------
    name : str
        Identifier/name for the node
    data_root : str or Path
        directory containing dataset with dicom files
    metadata_root : str or Path
        directory to store cache
    include_phantom
        Whether to include non-subject scans like localizer, acr/phantom,
        head_scout
    """

    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 include_phantom=False,
                 reindex=False):

        """
        Parameters
        ----------
        name : str
            an identifier/name for the dataset
        data_root : Path or str
            directory containing dicom files, supports nested hierarchies
        metadata_root : str or Path
            directory to store cache
        include_phantom : bool
            whether to include localizer/aahead_scout/phantom/acr
        reindex : bool
            If true, rejects stored cache and rebuilds index

        Examples
        --------
        >>> from MRdataset import xnat_dataset
        >>> dataset = xnat_dataset.XnatDataset()
        """
        super().__init__(name, data_root, metadata_root)

        self.include_phantom = include_phantom
        indexed = self.cache_path.exists()
        if not indexed or reindex:
            self.walk()
            self.save_dataset()
        else:
            self.load_dataset()

    def walk(self):
        """generates filenames in the directory tree, verifies if it is dicom
        file, extracts relevant parameters and stores it in project. Creates
        a desirable hierarchy for a neuroimaging experiment"""
        no_files_found = True
        study_ids_found = set()

        for filepath in files_under_folder(self.data_root):
            no_files_found = False
            try:
                if not dicom2nifti.common.is_dicom_file(filepath):
                    logger.warning("DICOM not found in {}".format(filepath.parent))
                    continue
                dicom = pydicom.read_file(filepath, stop_before_pixels=True)
                if common_dicom.is_valid_inclusion(filepath,
                                                   dicom,
                                                   self.include_phantom):

                    # info = common.parse_study_information(dicom)
                    modality_name = common_dicom.get_dicom_modality_tag(dicom)
                    modality_obj = self.get_modality(modality_name)
                    if modality_obj is None:
                        modality_obj = Modality(modality_name)

                    patient_id = str(dicom.PatientID)
                    subject_obj = modality_obj.get_subject(patient_id)
                    if subject_obj is None:
                        subject_obj = Subject(patient_id)

                    series_num = str(dicom.SeriesNumber)
                    session_node = subject_obj.get_session(series_num)
                    if session_node is None:
                        session_node = Session(series_num,
                                               Path(filepath).parent)

                    series_uid = dicom.SeriesInstanceUID
                    run_name = series_uid + '_e' + str(dicom.EchoNumbers)
                    run_node = session_node.get_run(run_name)
                    if run_node is None:
                        run_node = Run(run_name)
                        run_node.echo_time = dicom.EchoTime

                    dcm_img_params = common_dicom.parse_imaging_params(filepath)
                    if len(run_node.params) == 0:
                        run_node.params = dcm_img_params.copy()
                    elif param_difference(dcm_img_params, run_node.params):
                        raise config.ChangingParamsInSeries(filepath)

                    session_node.add_run(run_node)
                    subject_obj.add_session(session_node)
                    modality_obj.add_subject(subject_obj)
                    self.add_modality(modality_obj)

                    # Collect all unique study ids found in DICOM
                    study_ids_found.add(str(dicom.StudyID))

            except config.MRException as mrd_exc:
                logger.exception(mrd_exc)
            except Exception as exc:
                raise exc
        if no_files_found:
            raise EOFError("Read 0 files at {}".format(self.data_root))
        if len(study_ids_found) > 1:
            logger.warning(config.MultipleProjectsInDataset(study_ids_found))

