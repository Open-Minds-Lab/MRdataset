from MRdataset.utils import functional, common
from MRdataset.utils import progress
from MRdataset.data.base import Dataset
from pathlib import Path
from collections import defaultdict
import json
import warnings
import dicom2nifti
import logging


# TODO: check what if each variable is None. Apply try catch
class XnatDataset(Dataset):
    def __init__(self,
                 data_root=None,
                 metadata_root=None,
                 name='mind',
                 reindex=False,
                 verbose=False):
        """
        A dataset class for XNAT Dataset.
        Args:
            name:  an identifier/name for the dataset
            data_root: directory containing dataset with dicom files, supports nested hierarchies
            metadata_root: directory to store metadata files
            verbose: allow verbose output on console
            reindex: overwrite existing metadata files

        Examples:
            >>> from MRdataset.data import xnat_dataset
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
                warnings.warn("Generating metadata from dataset index. Use --reindex flag to regenerate index")
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
                with progress.Spinner():
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
        return self._subjects

    @property
    def modalities(self):
        return self._modalities

    @property
    def sessions(self):
        return self._sessions

    @property
    def projects(self):
        return self._projects

    def _create_metadata(self):
        raise NotImplementedError

    def walk(self):
        data_dict = functional.DeepDefaultDict(depth=3)
        for filename in self.data_root.glob('**/*.dcm'):
            try:
                if dicom2nifti.compressed_dicom.is_dicom_file(filename):
                    dicom = dicom2nifti.compressed_dicom.read_file(filename,
                                                                   stop_before_pixels=True)
                    if not dicom2nifti.convert_dir._is_valid_imaging_dicom(dicom):
                        logging.warning("Invalid file: %s" % filename)
                        continue
                    if not functional.header_exists(dicom):
                        logging.warning("Header Absent: %s" % filename)
                        continue
                    # modality = self._get_modality(dicom)
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

                    # Convert to string, because list is not hashable
                    if str(sid) not in self._modalities[series]:
                        self._modalities[series].append(sid)
                    if sid not in self._subjects:
                        self._subjects.append(sid)
                    if session not in self._sessions[sid]:
                        self._sessions[sid].append(session)
                    if project not in self._projects:
                        self._projects.append(project)

                    data_dict[sid][series]["id"] = session
                    data_dict[sid][series]["files"].append(filename.as_posix())
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
