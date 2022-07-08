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
                 reindex=False):

        """
        Args:
            data_root: directory containing dataset with dicom files, supports nested hierarchies
            metadata_root: directory to store metadata files
            name:  an identifier/name for the dataset
            reindex: overwrite existing metadata files
            verbose: allow verbose output on console

        Examples:
            >>> from MRdataset import xnat_dataset
            >>> dataset = xnat_dataset.XnatDataset()
        """
        super().__init__(name, data_root, metadata_root)
        self.cache_path = self.metadata_root / "{}.pkl".format(self.name)

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
                if common.is_valid_inclusion(filepath, dicom):
                    info = common.parse_study_information(dicom)

                    modality_obj = self.get_modality(info['modality'])
                    if modality_obj is None:
                        modality_obj = Modality(info['modality'])

                    subject_obj = modality_obj.get_subject(info['subject_name'])
                    if subject_obj is None:
                        subject_obj = Subject(info['subject_name'])

                    session_node = subject_obj.get_session(info['session_name'])
                    if session_node is None:
                        session_node = Session(info['session_name'],
                                               Path(filepath).parent)

                    run_node = session_node.get_run(info['run_name'])
                    if run_node is None:
                        run_node = Run(info['run_name'])
                        run_node.echo_time = info['echo_time']

                    dcm_img_params = common.parse_imaging_params(filepath)
                    if len(run_node.params) == 0:
                        run_node.params = dcm_img_params.copy()
                    elif param_difference(dcm_img_params, run_node.params):
                        raise config.ChangingParamsinSeries(filepath)

                    session_node.add_run(run_node)
                    subject_obj.add_session(session_node)
                    modality_obj.add_subject(subject_obj)
                    self.add_modality(modality_obj)

                    # Collect all unique study ids found in DICOM
                    study_ids_found.add(info['project'])

            except config.MRException as mrd_exc:
                logger.exception(mrd_exc)
            except Exception as exc:
                raise exc
        if len(study_ids_found) > 1:
            raise config.MultipleProjectsinDataset(study_ids_found)

    def __str__(self):
        return 'XnatDataset {0} was created with {1} modalities\n' \
               'Pass --name {0} to use generated cache\n'\
               .format(self.name, len(self.modalities))
