import logging
from pathlib import Path

import dicom2nifti
import pydicom
from MRdataset import common
from MRdataset import config
from MRdataset.base import Project, Run, Modality, Subject, Session
from MRdataset.utils import param_difference

# Module-level logger
logger = logging.getLogger('root')


# TODO: check what if each variable is None. Apply try catch
class XnatDataset(Project):
    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 include_phantom=False,
                 reindex=False):

        """
                @param data_root: directory containing dataset with dicom files,
        supports nested hierarchies
        @param metadata_root: directory to store cache
        @param name:  an identifier/name for the dataset
        @param reindex: overwrite existing cache



        Parameters
        ----------
        name
        data_root
        metadata_root
        include_phantom
        reindex

        Examples
        --------
        >>> from MRdataset import xnat_dataset
        >>> dataset = xnat_dataset.XnatDataset()
        """
        super().__init__(name, data_root, metadata_root)
        self.cache_path = self.metadata_root / "{}.pkl".format(self.name)
        self.include_phantom = include_phantom
        indexed = self.cache_path.exists()
        if not indexed or reindex:
            self.walk()
            self.save_dataset()
        else:
            self.load_dataset()

    def walk(self):
        study_ids_found = set()
        for filepath in self.data_root.glob('**/*.dcm'):
            try:
                if not dicom2nifti.common.is_dicom_file(filepath):
                    continue
                dicom = pydicom.read_file(filepath, stop_before_pixels=True)
                if common.is_valid_inclusion(filepath,
                                             dicom,
                                             self.include_phantom):

                    # info = common.parse_study_information(dicom)
                    modality_name = common.get_dicom_modality_tag(dicom)
                    modality_obj = self.get_modality(modality_name)
                    if modality_obj is None:
                        modality_obj = Modality(modality_name)

                    patient_name = str(dicom.PatientName)
                    subject_obj = modality_obj.get_subject(patient_name)
                    if subject_obj is None:
                        subject_obj = Subject(patient_name)

                    series_uid = str(dicom.SeriesInstanceUID)
                    session_node = subject_obj.get_session(series_uid)
                    if session_node is None:
                        session_node = Session(series_uid,
                                               Path(filepath).parent)

                    run_name = series_uid + '_e' + str(dicom.EchoNumbers)
                    run_node = session_node.get_run(run_name)
                    if run_node is None:
                        run_node = Run(run_name)
                        run_node.echo_time = dicom.EchoTime

                    dcm_img_params = common.parse_imaging_params(filepath)
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
        if len(study_ids_found) > 1:
            logger.warning(config.MultipleProjectsInDataset(study_ids_found))

    def __str__(self):
        return 'XnatDataset {0} was created with {1} modalities\n' \
               'Pass --name {0} to use generated cache\n'\
               .format(self.name, len(self.modalities))
