import MRdataset.common
import MRdataset.utils
from MRdataset.utils import common
from MRdataset.base import Dataset
from pathlib import Path
from collections import defaultdict
import json
import warnings
import dicom2nifti
import logging
import pydicom


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

        self.json_path = self.metadata_root / "{0}.json".format(self.name)
        self.metadata_path = self.metadata_root / "{0}.json".format(self.name + '_metadata')

        self.indexed = self.json_path.exists()
        if self.indexed:
            if not self.metadata_path.exists():
                warnings.warn("Expected {name}_metadata.json. Got None. "
                              "Re-generating metadata from old dataset index. Use --reindex flag to regenerate index")
                self._create_metadata()

        # Private Placeholders for metadata
        self._subjects = []
        self._modalities = defaultdict(list)
        self._sessions = defaultdict(list)
        self._projects = []

        # Start indexing
        self.verbose = verbose
        if not self.indexed or reindex:
            if self.verbose:
                print("Indexing dataset.", end="...")
                with MRdataset.utils.Spinner():
                    self.data = self.walk()
                print("\n")
            else:
                self.data = self.walk()
        else:
            if self.verbose:
                print("Metadata files found.")

            with open(self.json_path, 'r') as f:
                self.data = json.load(f)

            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            self._subjects = metadata['subjects']
            self._modalities = metadata['modalities']
            self._sessions = metadata['sessions']
            self._projects = metadata.get('projects', list())

    @property
    def subjects(self):
        """
        Collection of all subjects in the folder.
        """
        return self._subjects

    @property
    def modalities(self):
        """
        Collection of all modalities, grouped by subjects.
        """
        return self._modalities

    @property
    def sessions(self):
        """
        Collection of all unique SeriesInstanceUID, grouped by subject id
        """
        return self._sessions

    @property
    def projects(self):
        """
        Collection of all Study ID values in the dataset. Can be used to decide if
        the folder contains different scans from different projects
        """
        return self._projects

    def _create_metadata(self):
        raise NotImplementedError

    def walk(self):
        data_dict = functional.DeepDefaultDict(depth=3)
        for filename in self.data_root.glob('**/*.dcm'):
            try:
                if dicom2nifti.common.is_dicom_file(filename):
                    dicom = pydicom.read_file(filename,
                                              stop_before_pixels=True)
                    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
                        logging.warning("Invalid file: %s" % filename)
                        continue
                    if not MRdataset.common.header_exists(dicom):
                        logging.warning("Header Absent: %s" % filename)
                        continue
                    echo_number = common.get_echo_number(dicom)

                    # TODO should we call it a modality? i think we should
                    series = common.get_series(dicom)

                    # TODO: make the check more concrete. See dicom2nifti for details
                    if 'local' in series.lower():
                        logging.warning("Localizer: Skipping %s" % filename)
                        continue

                    session = common.get_session(dicom)
                    sid = common.get_subject(dicom)
                    if ('acr' in sid.lower()) or ('phantom' in sid.lower()):
                        logging.warning('ACR/Phantom: %s' % filename)
                        continue

                    project = common.get_project(dicom)

                    # MRIcrogl detected 2 different series in a single folder
                    # Even though Series Instance UID was same, there was
                    # a difference in echo number, for gre_field_mapping
                    run = session + '_e' + str(echo_number)
                    # Convert to string, because list is not hashable
                    if str(sid) not in self._modalities[series]:
                        self._modalities[series].append(sid)
                    if sid not in self._subjects:
                        self._subjects.append(sid)
                    if run not in self._sessions[sid]:
                        self._sessions[sid].append(run)
                    if project not in self._projects:
                        self._projects.append(project)

                    # data_dict[sid][series][run] = run
                    data_dict[sid][series][run].append(filename.as_posix())
            except Exception as e:
                logging.warning("Unable to read: %s" % filename)
                logging.exception(e)

        with open(self.json_path, "w") as file:
            json.dump(dict(data_dict), file, indent=4)

        self.is_unique_project()

        metadata = {
            "subjects": self.subjects,
            "modalities": self.modalities,
            "sessions": self.sessions,
            "projects": self.projects
        }
        with open(self.metadata_path, "w") as file:
            json.dump(dict(metadata), file, indent=4)

        return data_dict

    def is_unique_project(self):
        if len(self.projects) > 1:
            logging.warning("Expected all the dicom files to be in the same project/study. "
                            "Found {0} unique project/study id(s)".format(len(self.projects)))
            return False
        if len(self.projects) == 1:
            if self.projects[0] is None:
                logging.warning("Unique project/study id not found. Assuming that all dicom "
                                "files to be in the same project.")
                return False
            return True
        logging.warning("Error in processing! self.projects is empty")
        return False

    def __str__(self):
        return 'XnatDataset {1} was created\n' \
               'Please use identifier {1} with --name flag to utilize generated cache\n' \
               '#Subject: {0}'.format(len(self.subjects), self.name)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sid, session = idx
        try:
            value = self.data[sid][session]
            return value
        except KeyError:
            logging.warning("Index ({0}, {1}) absent. Skipping. Do you want to regenerate index?".format(sid, session))
