import logging
import pickle
from pathlib import Path
import dicom2nifti
import pydicom
from MRdataset import common
from MRdataset import config
from MRdataset.base import Node, Run, Modality, Subject, Session
from MRdataset.utils import param_difference


# TODO: check what if each variable is None. Apply try catch
class XnatDataset(Node):
    def __init__(self,
                 name='mind',
                 data_root=None,
                 metadata_root=None,
                 reindex=False,
                 verbose=False):

        """
        Container to manage properties and issues at the project level.
        Encapsulates all the details necessary for a complete project.
        A single project may contain multiple modalities, and each modality
        will have atleast single subject.

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
        super().__init__(name)

        # Manage directories
        self.data_root = Path(data_root)
        if not self.data_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.metadata_root = Path(metadata_root)
        if not self.metadata_root.exists():
            raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        self.cache_path = self.metadata_root / "{}.pkl".format(self.name)
        indexed = self.cache_path.exists()
        if not indexed or reindex:
            self.walk()
            self.save_dataset()
        else:
            self.load_dataset()

        print(self)

    @property
    def modalities(self):
        return self._children

    def add_modality(self, new_modality):
        self.__add__(new_modality)

    def get_modality(self, name):
        return self._get(name)

    def save_dataset(self):
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.__dict__, f)

    def load_dataset(self):
        with open(self.cache_path, 'rb') as f:
            temp_dict = pickle.load(f)
            self.__dict__.update(temp_dict)

    def walk(self):
        study_ids_found = set()
        for filepath in self.data_root.glob('**/*.dcm'):
            try:
                if not dicom2nifti.common.is_dicom_file(filepath):
                    return False
                dicom = pydicom.read_file(filepath,
                                          stop_before_pixels=True)
                if common.is_valid_file(filepath, dicom):
                    dcm_echo_number = common.get_tags_by_name(dicom, 'echo_number')
                    dcm_project_name = common.get_tags_by_name(dicom, 'study_id')
                    dcm_modality_name = common.get_dicom_modality(dicom)
                    dcm_subject_name = common.get_tags_by_name(dicom, 'patient_name')
                    dcm_session_name = common.get_tags_by_name(dicom, 'series_number')
                    dcm_series_instance_uid = common.get_tags_by_name(dicom, 'series_instance_uid')

                    modality_node = self.get_modality(dcm_modality_name)
                    if modality_node is None:
                        modality_node = Modality(dcm_modality_name)

                    subject_node = modality_node.get_subject(dcm_subject_name)
                    if subject_node is None:
                        subject_node = Subject(dcm_subject_name)

                    session_node = subject_node.get_session(dcm_session_name)
                    if session_node is None:
                        session_node = Session(dcm_session_name, Path(filepath).parent)

                    # dcm2niix detected 2 different series in a single folder
                    # Even though Series Instance UID was same, there was
                    # a difference in echo number, for gre_field_mapping
                    run_name = dcm_series_instance_uid + '_e' + str(dcm_echo_number)

                    run_node = session_node.get_run(run_name)
                    if run_node is None:
                        run_node = Run(run_name)

                    dcm_params = common.parse(filepath)
                    if len(run_node.params) == 0:
                        run_node.params = dcm_params.copy()
                    elif param_difference(dcm_params, run_node.params):
                        raise config.ChangingParamsinSeries(filepath)

                    session_node.add_run(run_node)
                    subject_node.add_session(session_node)
                    modality_node.add_subject(subject_node)
                    self.add_modality(modality_node)

                    # Collect all unique study ids found in DICOM
                    study_ids_found.add(dcm_project_name)

            except config.MRdatasetException as e:
                logging.exception(e)
        if len(study_ids_found) > 1:
            raise config.MultipleProjectsinDataset(study_ids_found)

    def __str__(self):
        return 'XnatDataset {0} was created with {1} modalities\n' \
               'Pass --name {0} to use generated cache\n'.format(self.name, len(self.modalities))
