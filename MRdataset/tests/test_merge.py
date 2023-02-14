import unittest
from MRdataset import import_dataset
import zipfile
from pathlib import Path


class TestMergeDatasets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        zip_path = '../../examples/test_merge_data.zip'
        temp_dir = Path('/tmp/')
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        cls.complete_dataset = import_dataset(
            data_source=temp_dir/'test_merge_data/full_data')
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
        ds1 = import_dataset(data_source=folder_path/'set1')
        ds2 = import_dataset(data_source=folder_path/'set2')
        ds1.merge(ds2)
        assert self.is_same_dataset(ds1, self.complete_dataset)

    @staticmethod
    def is_same_dataset(dataset1, dataset2):
        modalities_list1 = sorted(dataset1.modalities)
        modalities_list2 = sorted(dataset2.modalities)
        for modality1, modality2 in zip(modalities_list1, modalities_list2):
            assert modality1.name == modality2.name
            assert modality1.compliant == modality2.compliant
            assert modality1._reference == modality2._reference
            assert modality1.non_compliant_data.equals(modality2.non_compliant_data)
            subjects_list1 = sorted(modality1.subjects)
            subjects_list2 = sorted(modality2.subjects)
            for subject1, subject2 in zip(subjects_list1, subjects_list2):
                assert subject1.name == subject2.name
                assert subject1.__dict__ == subject2.__dict__
                sessions_list1 = sorted(subject1.sessions)
                sessions_list2 = sorted(subject2.sessions)
                for session1, session2 in zip(sessions_list1, sessions_list2):
                    assert session1.name == session2.name
                    assert session1.__dict__ == session2.__dict__
                    runs_list1 = sorted(session1.runs)
                    runs_list2 = sorted(session2.runs)
                    for run1, run2 in zip(runs_list1, runs_list2):
                        assert run1.__dict__ == run2.__dict__
                        assert run1.name == run2.name
                        assert run1.params == run2.params
        return True
