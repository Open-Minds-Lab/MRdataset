from MRdataset.utils import functional
from MRdataset.utils import progress
from MRdataset.core.basemrdataset import Dataset
from pathlib import Path
import json
import pydicom
from collections import defaultdict
import warnings

class XnatDataset(Dataset):
    def __init__(self,
                 name='mind',
                 style='local',
                 data_dir=None,
                 verbose=True,
                 reindex=False,
                 combine=True):
        """

        """
        default_data_dir = "/media/harsh/My Passport/MRI_Datasets/sinhah-20220514_140054/"
        self.DATA_DIR = Path(data_dir) if data_dir else Path(default_data_dir)
        if not self.DATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        json_filename = "resources/{0}.json".format(name)
        self.json_path = Path(__file__).resolve().parent/json_filename
        metadata_filename = "resources/{0}.json".format(name+'_metadata')
        self.metadata_path = Path(__file__).resolve().parent/metadata_filename

        self.indexed = self.json_path.exists()

        self._subjects = []
        self._modalities = defaultdict(list)
        self._sessions = defaultdict(list)
        # self.subjects = list

        # Constants
        self.SESSION_TAG = (0x20, 0x0e)
        self.SEQUENCE_TAG = (0x18, 0x20)
        self.VARIANT_TAG = (0x18, 0x21)
        self.SUBJECT_TAG = (0x10, 0x10)

        self.verbose = verbose
        if not self.indexed or reindex:
            if self.verbose:
                print("JSON file not found, It will take sometime to skim the dataset.", end="...")
            with progress.Spinner():
                self.data = self.walk()
        else:
            if self.verbose:
                print("JSON file found.")

            with open(self.json_path, 'r') as f:
                self.data = json.load(f)
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            self._subjects = metadata['subjects']
            self._modalities = metadata['modalities']
            self._sessions = metadata['sessions']

        print(self)

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
        series = dicom.get(self.SESSION_TAG, None).value
        return series

    def get_modality(self, dicom):
        mode = []
        sequence = dicom.get(self.SEQUENCE_TAG, None).value
        variant = dicom.get(self.VARIANT_TAG, None).value
        # If string, append to list
        # If list, convert expression to list, append to list
        if isinstance(sequence, str):
            mode.append(sequence)
        elif isinstance(sequence, pydicom.multival.MultiValue):
            mode.append(list(sequence))
        else:
            warnings.warn("Error reading modality. Skipping.")
        if isinstance(variant, str):
            mode.append(variant)
        elif isinstance(variant, pydicom.multival.MultiValue):
            mode.append(list(variant))
        else:
            warnings.warn("Error reading modality. Skipping.")

        return functional.flatten(mode)

    def get_subject(self, dicom):
        name = str(dicom.get(self.SUBJECT_TAG, None).value)
        return name

    def walk(self):
        data_dict = functional.DeepDefaultDict(depth=3)
        i = 0
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

            # if i > 100000:
            #     break
            # i += 1
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
        return '\n#Files : {0}    \n' \
               '#Subject: {1}'.format(len(self), len(self.subjects))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sid, session = idx
        obj = self.data[sid][session]
        return obj


if __name__ == "__main__":
    dataset = XnatDataset(reindex=True)
    # print(dataset.__getitem__(0))
