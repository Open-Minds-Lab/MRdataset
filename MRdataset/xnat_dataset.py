import logging
import pickle
from pathlib import Path

import dicom2nifti
import pydicom
from MRdataset import common
from MRdataset import config
from MRdataset.base import Dataset, Project, Run, Modality, Subject


# TODO: check what if each variable is None. Apply try catch
class XnatDataset(Dataset):
    def __init__(self,
                 data_root=None,
                 metadata_root=None,
                 name='mind',
                 reindex=False,
                 verbose=False):
        """
        Class defining an XNAT dataset class. Encapsulates all the details necessary for execution
        hence easing the subsequent analysis/workflow.

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
        super().__init__()
        self.name = name

        # Manage directories
        self.data_root = Path(data_root)
        if not self.data_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.metadata_root = Path(metadata_root)
        if not self.metadata_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        cache_path = self.metadata_root / "{}.pkl".format(self.name)
        indexed = cache_path.exists()

        if not indexed or reindex:
            self.project_node = Project(name=self.name)
            self.walk()
            with open(cache_path, "wb") as f:
                pickle.dump(self.project_node, f)
        else:
            with open(cache_path, 'rb') as f:
                self.project_node = pickle.load(f)

    @property
    def modalities(self):
        """
        Collection of all modalities, grouped by subjects.
        """
        return self._modalities

    @property
    def projects(self):
        """
        Collection of all Study ID values in the dataset. Can be used to decide if
        the folder contains different scans from different projects
        """
        return self._projects

    # def _create_metadata(self):
    #     raise NotImplementedError

    def is_valid_file(self, filename, dicom):
        if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
            logging.warning("Invalid file: %s" % filename)
            return False

        if not common.header_exists(dicom):
            logging.warning("Header Absent: %s" % filename)
            return False

        # TODO: make the check more concrete. See dicom2nifti for details
        if 'local' in common.get_dicom_modality(dicom).lower():
            logging.warning("Localizer: Skipping %s" % filename)
            return False

        sid = common.get_subject(dicom)
        if ('acr' in sid.lower()) or ('phantom' in sid.lower()):
            logging.warning('ACR/Phantom: %s' % filename)
            return False

        # TODO: Add checks to remove aahead_64ch_head_coil

        return True

    def walk(self):
        study_ids_found = set()
        for filepath in self.data_root.glob('**/*.dcm'):
            try:
                if not dicom2nifti.common.is_dicom_file(filepath):
                    return False
                dicom = pydicom.read_file(filepath,
                                          stop_before_pixels=True)
                if self.is_valid_file(filepath, dicom):
                    dcm_echo_number = common.get_tags_by_name(dicom, 'echo_number')
                    dcm_project_name = common.get_tags_by_name(dicom, 'study_id')
                    dcm_modality_name = common.get_dicom_modality(dicom)
                    dcm_subject_name = common.get_tags_by_name(dicom, 'patient_name')
                    dcm_series_instance_uid = common.get_tags_by_name(dicom, 'series_instance_uid')

                    modality_node = self.project_node.get_modality(dcm_modality_name)
                    if modality_node is None:
                        modality_node = Modality(dcm_modality_name)

                    subject_node = modality_node.get_subject(dcm_subject_name)
                    if subject_node is None:
                        subject_node = Subject(dcm_subject_name, Path(filepath).parent)

                    # dcm2niix detected 2 different series in a single folder
                    # Even though Series Instance UID was same, there was
                    # a difference in echo number, for gre_field_mapping
                    run_name = dcm_series_instance_uid + '_e' + str(dcm_echo_number)

                    run_node = subject_node.get_run(run_name)
                    if run_node is None:
                        run_node = Run(run_name)

                    dcm_params = common.parse(filepath)
                    if len(run_node.params) == 0:
                        run_node.params = dcm_params.copy()
                    elif run_node.param_difference(dcm_params):
                        raise config.ChangingParamsinSeries(filepath)

                    subject_node.add_run(run_node)
                    modality_node.add_subject(subject_node)
                    self.project_node.add_modality(modality_node)
                    study_ids_found.add(dcm_project_name)

            except config.MRdatasetException as e:
                logging.exception(e)
        if len(study_ids_found) > 1:
            raise config.MultipleProjectsinDataset(study_ids_found)

    def __str__(self):
        return 'XnatDataset {} was created\n' \
               'Pass --name {} to use generated cache\n'.format(self.name)
