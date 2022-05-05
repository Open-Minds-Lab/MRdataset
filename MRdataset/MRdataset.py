"""Main module."""

from abc import ABC


class BaseMRDataset(ABC):
    """Base class for container classes holding MRI datasets: XNAT, BIDS, DICOM"""

    def __int__(self, name='dataset', type='XNAT'):

        self.name = name
        self.type = type

        self.projects = dict()
        self.subjects = dict()
        self.sessions = dict()



class XnatDataset(BaseMRDataset):

    def __int__(self, path, name='XNAT'):
        """Constuctor"""

        super().__int__(name=name, type='XNAT')

        self.load(path=path)


    def load(self, path):
        """populates the class with underlying structure"""




    def traveser(self):
        """iterator in heirarchical fashion"""





