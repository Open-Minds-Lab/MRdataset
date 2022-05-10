from MRdataset.core.basemrdataset import Dataset
from pathlib import Path
import json


class LocalDataset(Dataset):
    def __init__(self,
                 name='bold',
                 type='local',
                 data_dir=None,
                 verbose=True,
                 reindex=False):
        self.DATA_DIR = Path(data_dir) if data_dir else Path("/media/harsh/My Passport/BOLD5000")
        if not self.DATA_DIR.exists():
            raise FileNotFoundError('Provide a valid /path/to/dataset/')

        json_filename = "resources/{0}.json".format(name)
        self.json_path = Path(__file__).resolve().parent/json_filename
        self.indexed = self.json_path.exists()

        if not self.indexed or reindex:
            if verbose:
                print("JSON file not found, It will take sometime to skim the dataset.")
            self.objects = self.walk()
        else:
            if verbose:
                print("JSON file found.")
            with open(self.json_path, 'r') as f:
                self.objects = json.loads(f.read())

        print(self)

    def walk(self):
        data_dict = []
        for filename in self.DATA_DIR.glob('**/*.dcm'):
            data_dict.append(str(filename))
        with open(self.json_path, "w") as file:
            file.write(json.dumps(data_dict))
        return data_dict

    def __str__(self):
        return '#Files : {0}'.format(len(self))

    def make_dataset(self):
        objects = []
        missing_objects = []
        for f in self.objects:
            if not f.exists():
                missing_objects.append(f)
        if len(missing_objects) > 0:
            print("Data missing : ", *missing_objects)
        return objects

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, idx):
        obj = self.objects[idx]
        return obj


if __name__ == "__main__":
    dataset = LocalDataset()
    print(dataset.__getitem__(0))
