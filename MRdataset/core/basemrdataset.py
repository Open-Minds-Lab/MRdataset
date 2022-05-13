from abc import ABC, abstractmethod


class Dataset(ABC):
    """An abstract class representing a dataset"""

    @abstractmethod
    def __getitem__(self, idx):
        raise NotImplementedError("__getitem__ attribute implementation for dataset is missing.")

    @abstractmethod
    def __len__(self):
        raise TypeError("__len__ attribute implementation for dataset is missing.")

# class BaseMRDataset(Dataset):
#     """Base class for container classes holding MRI datasets: XNAT, BIDS, DICOM"""
#
#     def __int__(self, name='dataset', type='XNAT'):
#
#         self.name = name
#         self.type = type
#
#         self.projects = dict()
#         self.subjects = dict()
#         self.sessions = dict()




