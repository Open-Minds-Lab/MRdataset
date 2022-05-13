import warnings
from MRdataset.utils.functional import DeepDefaultDict, flatten
from MRdataset.core.basemrdataset import Dataset
from pathlib import Path
import json
import pydicom
from collections import defaultdict
from tqdm import tqdm
from pprint import pprint
import itertools

class LocalDataset(Dataset):
    def __init__(self,
                 name='bold',
                 type='local',
                 data_dir=None,
                 verbose=True,
                 reindex=False,
                 combine=True):
        self.DATA_DIR = Path(data_dir) if data_dir else Path("/media/harsh/My Passport/BOLD5000")
        if not self.DATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        json_filename = "resources/{0}.json".format(name)
        self.json_path = Path(__file__).resolve().parent/json_filename
        metadata_filename = "resources/{0}.json".format(name+'_metadata')
        self.metadata_path = Path(__file__).resolve().parent/metadata_filename

        self.indexed = self.json_path.exists()

        self._subjects = defaultdict(list)
        self._modalities = defaultdict(list)
        self._sessions = defaultdict(list)

        # Constants
        self.SESSION_TAG = (0x20, 0x0e)
        self.SEQUENCE_TAG = (0x18, 0x20)
        self.VARIANT_TAG = (0x18, 0x21)
        self.SUBJECT_TAG = (0x10, 0x10)

        self.verbose = verbose
        if not self.indexed or reindex:
            if self.verbose:
                print("JSON file not found, It will take sometime to skim the dataset.")
            self.objects = self.walk()
        else:
            if self.verbose:
                print("JSON file found.")
            with open(self.json_path, 'r') as f:
                self.objects = json.load(f)
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
            self._subjects = metadata['subjects']
            self._modalities = metadata['modalities']
            self._sessions = metadata['sessions']

        # self.make_dataset()
        self.combine_subjects_dir = combine
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
        mode.append(sequence)
        mode.append(list(variant))
        return flatten(mode)

    def get_subject(self, dicom):
        name = str(dicom.get(self.SUBJECT_TAG, None).value)
        return name

    def walk(self):
        data_dict = DeepDefaultDict(depth=4)
        for subject in self.DATA_DIR.iterdir():
            if subject.is_dir():
                print(".")
                i = 0
                for filename in self.DATA_DIR.glob('**/*.dcm'):
                    dicom = pydicom.dcmread(filename)
                    modality = self.get_modality(dicom)
                    run = self.get_session(dicom)
                    sid = self.get_subject(dicom)

                    sub = subject.as_posix()
                    if str(modality) not in self._modalities[sub]:
                        self._modalities[sub].append(str(modality))
                    if sid not in self._subjects[sub]:
                        self._subjects[sub].append(sid)
                    if run not in self._sessions[sub]:
                        self._sessions[sub].append(run)
                    data_dict[sub][sid][run]["mode"] = modality
                    data_dict[sub][sid][run]["files"].append(filename.as_posix())

                    if i > 100:
                        break
                    else:
                        i += 1

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
        return '#Files : {0}    \n' \
               '#Subject: {1}'.format(len(self), len(self.subjects))

    def make_dataset(self):
        objects = []
        missing_objects = []
        for subject in self.data_dict.keys():
            for sid in self.data_dict[subject].keys():
                for session in self.data_dict[subject][sid].keys():
                    modality = self.data_dict[subject][sid][session]["mode"]
                    files = self.data_dict[subject][sid][session]["files"]
                    # for f in files:
                        # if not Path(f).exists():
                            # missing_objects.append(f)
                    objects.append(self.data_dict[subject][sid][session])
        if len(missing_objects) > 0:
            print("Data missing : ", *missing_objects)
        return objects

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, idx):
        obj = self.objects[idx]
        return obj


if __name__ == "__main__":
    dataset = LocalDataset(reindex=True)
    print(dataset.__getitem__(0))
