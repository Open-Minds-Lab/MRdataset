import unittest
import zipfile
from pathlib import Path

import pytest
from MRdataset import import_dataset

THIS_DIR = Path(__file__).parent.resolve()

class TestMergeDatasets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        zip_path = THIS_DIR / 'resources/test_merge_data.zip'
        if not Path(zip_path).is_file():
            raise FileNotFoundError(f'Expected valid file for --data_source argument, '
                                     f'Got {zip_path}')
        temp_dir = Path('/tmp/')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        cls.complete_dataset = import_dataset(
            data_source=temp_dir/'test_merge_data/full_data',
            ds_format='dicom',
            config_path=THIS_DIR / 'resources/mri-config.json',
            output_dir=temp_dir, name='test_dataset')
        cls.data_source = temp_dir/'test_merge_data'

    def test_modalities(self):
        folder_path = self.data_source/'new_modalities'
        self.merge_and_check(folder_path)

    def test_subjects(self):
        folder_path = self.data_source/'new_subjects'
        self.merge_and_check(folder_path)

    def test_sessions(self):
        folder_path = self.data_source/'new_sessions'
        self.merge_and_check(folder_path)

    def test_runs(self):
        folder_path = self.data_source/'new_runs'
        self.merge_and_check(folder_path)

    def merge_and_check(self, folder_path):
        ds1 = import_dataset(data_source=folder_path/'set1', ds_format='dicom',
                             config_path=THIS_DIR / 'resources/mri-config.json',
                             output_dir=folder_path, name='test_dataset')
        ds2 = import_dataset(data_source=folder_path/'set2', ds_format='dicom',
                             config_path=THIS_DIR / 'resources/mri-config.json',
                             output_dir=folder_path, name='test_dataset')
        assert ds1 != ds2
        ds1.merge(ds2)
        assert self.is_same_dataset(ds1, self.complete_dataset)

        with pytest.raises(TypeError):
            ds1.merge(None)

        with pytest.raises(ValueError):
            ds2.format = 'invalid_format'
            ds1.merge(ds2)

    @staticmethod
    def is_same_dataset(dataset1, dataset2):
        for seq_id in dataset2.get_sequence_ids():
            for subject, session, run, seq2 in dataset2.traverse_horizontal(seq_id=seq_id):
                seq1 = dataset1.get(subject_id=subject, session_id=session,
                                    run_id=run, seq_id=seq2.name)
                assert seq1 == seq2
        return True
