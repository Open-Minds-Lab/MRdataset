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


class XnatDataset(Dataset):
    def __init__(self,
                 name='mind',
                 input=None,
                 metadata=None,
                 verbose=False,
                 reindex=False,
                 **kwargs):
        """
        A dataset class for XNAT Dataset.
        Args:
            name:  an identifier/name for the dataset
            input: directory containing dataset with dicom files, supports nested hierarchies
            metadata: directory to store metadata files
            verbose: allow verbose output on console
            reindex: overwrite existing metadata files

        Examples:
            >>> from MRdataset.data import xnat_dataset
            >>> dataset = xnatdataset.XnatDataset()
        """
        # Manage directories
        self.DATA_DIR = Path(input)
        if not self.DATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        self.METADATA_DIR = Path(metadata)
        if not self.METADATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/metadata/dir')

        self.json_path = self.METADATA_DIR/"{0}.json".format(name)
        self.metadata_path = self.METADATA_DIR/"{0}.json".format(name+'_metadata')
        self.indexed = self.json_path.exists()

        # Private Placeholders for metadata
        self._subjects = []
        self._modalities = defaultdict(list)
        self._sessions = defaultdict(list)

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

    @property
    def subjects(self):
        return self._subjects

    @property
    def modalities(self):
        return self._modalities

    @property
    def sessions(self):
        return self._sessions

    def get_session(self, dicom):
        series = dicom.get(config.SESSION, None).value
        return series

    def get_modality(self, dicom):
        mode = []
        sequence = dicom.get(config.SEQUENCE, None).value
        variant = dicom.get(config.VARIANT, None).value

        # If string, append to list
        # If pydicom.multival.MultiValue, convert expression to list, append to list
        if isinstance(sequence, str):
            mode.append(sequence)
        elif isinstance(sequence, MultiValue):
            mode.append(list(sequence))
        else:
            warnings.warn("Error reading modality. Skipping.")
        if isinstance(variant, str):
            mode.append(variant)
        elif isinstance(variant, MultiValue):
            mode.append(list(variant))
        else:
            warnings.warn("Error reading modality. Skipping.")

        return functional.flatten(mode)

    def get_subject(self, dicom):
        name = str(dicom.get(config.SUBJECT, None).value)
        return name

    def walk(self):
        data_dict = functional.DeepDefaultDict(depth=3)
        # from random import shuffle
        for filename in self.DATA_DIR.glob('**/*.dcm'):
            dicom = pydicom.dcmread(filename)
            modality = self.get_modality(dicom)
            session = self.get_session(dicom)
            sid = self.get_subject(dicom)

            # sub = subject.as_posix()
            if str(modality) not in self._modalities[sid]:
                self._modalities[sid].append(str(modality))
            if sid not in self._subjects:
                self._subjects.append(sid)
            if session not in self._sessions[sid]:
                self._sessions[sid].append(session)

            data_dict[sid][session]["mode"] = modality
            data_dict[sid][session]["files"].append(filename.as_posix())

        with open(self.json_path, "w") as file:
            json.dump(dict(data_dict), file, indent=4)

        metadata = {
            "subjects": self.subjects,
            "modalities": self.modalities,
            "sessions": self.sessions
        }
        with open(self.metadata_path, "w") as file:
            json.dump(dict(metadata), file, indent=4)

        return data_dict

    def __str__(self):
        return 'XnatDataset was created\n' \
               '#Files : {0}    \n' \
               '#Subject: {1}'.format(len(self), len(self.subjects))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sid, session = idx
        return self.data[sid][session]
