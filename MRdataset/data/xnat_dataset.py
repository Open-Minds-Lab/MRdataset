from MRdataset.utils import functional
from MRdataset.utils import progress
from MRdataset.data.base import Dataset
from MRdataset.data import config
from pathlib import Path
from collections import defaultdict
from pydicom.multival import MultiValue
import json
import pydicom
import warnings


# TODO: check what if each variable is None. Apply try catch
# TODO: generate metadata from index, if metadata is absent
class XnatDataset(Dataset):
    def __init__(self,
                 name='mind',
                 dataroot=None,
                 metadataroot=None,
                 verbose=False,
                 reindex=False,
                 **kwargs):
        """
        A dataset class for XNAT Dataset.
        Args:
            name:  an identifier/name for the dataset
            dataroot: directory containing dataset with dicom files, supports nested hierarchies
            metadataroot: directory to store metadata files
            verbose: allow verbose output on console
            reindex: overwrite existing metadata files

        Examples:
            >>> from MRdataset.data import xnat_dataset
            >>> dataset = xnat_dataset.XnatDataset()
        """
        super().__init__()
        # Manage directories
        self.DATA_DIR = Path(dataroot)
        if not self.DATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.METADATA_DIR = Path(metadataroot)
        if not self.METADATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        self.json_path = self.METADATA_DIR/"{0}.json".format(name)
        self.metadata_path = self.METADATA_DIR/"{0}.json".format(name+'_metadata')
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

    # TODO: Move to baseclass
    def _get_property(self, dicom, attribute):
        element = dicom.get(getattr(config, attribute), None)
        if not element:
            return None
        return element.value

    def _get_project(self, dicom):
        return self._get_property(dicom, 'STUDY')

    def _get_session(self, dicom):
        return self._get_property(dicom, 'SESSION')

    def _get_modality(self, dicom):
        mode = []
        sequence = self._get_property(dicom, 'SEQUENCE')
        variant = self._get_property(dicom, 'VARIANT')

        # If string, append to list
        # If pydicom.multival.MultiValue, convert expression to list, append to list
        if isinstance(sequence, str):
            mode.append(sequence)
        elif isinstance(sequence, MultiValue):
            mode.append(list(sequence))
        else:
            warnings.warn("Error reading <sequence>. Do you think its a phantom?")
        if isinstance(variant, str):
            mode.append(variant)
        elif isinstance(variant, MultiValue):
            mode.append(list(variant))
        else:
            warnings.warn("Error reading <variant>. Do you think its a phantom?")

        return functional.flatten(mode)

    def _get_subject(self, dicom):
        return str(self._get_property(dicom, 'SUBJECT'))

    def walk(self):
        data_dict = functional.DeepDefaultDict(depth=3)
        for filename in self.DATA_DIR.glob('**/*.dcm'):
            dicom = pydicom.dcmread(filename)
            modality = self._get_modality(dicom)
            session = self._get_session(dicom)
            sid = self._get_subject(dicom)
            project = self._get_project(dicom)

            # Convert to string, because list is not hashable
            if str(modality) not in self._modalities[sid]:
                self._modalities[sid].append(str(modality))
            if sid not in self._subjects:
                self._subjects.append(sid)
            if session not in self._sessions[sid]:
                self._sessions[sid].append(session)
            if project not in self._projects:
                self._projects.append(project)

            data_dict[sid][session]["mode"] = modality
            data_dict[sid][session]["files"].append(filename.as_posix())

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
            warnings.warn("Expected all the dicom files to be in the same project/study. "
                          "Found {0} unique project/study id(s)".format(len(self.projects)))
            return False
        if len(self.projects) == 1:
            if self.projects[0] is None:
                warnings.warn("Unique project/study id not found. Assuming that all dicom "
                              "files to be in the same project.")
                return False
            return True
        warnings.warn("Error in processing! self.projects is empty")
        return False

    def __str__(self):
        return 'XnatDataset {1} was created\n' \
               '#Subject: {0}'.format(len(self.subjects), self.name)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sid, session = idx
        try:
            value = self.data[sid][session]
            return value
        except KeyError:
            warnings.warn("Index ({0}, {1}) absent. Skipping. Do you want to regenerate index?".format(sid, session))

